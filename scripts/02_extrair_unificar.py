#!/usr/bin/env python3
"""
02 — Ingestão 2018–2025: extrai os CSVs mensais dos ZIPs particionados
(pasta Drive Multas_Part), transcodifica para UTF-8 e unifica em UM
arquivo por ano em dados_brutos/infracoes_<ANO>.csv.

Regras:
  - Ordem cronológica de meses (inclui sufixos 12a/12b de 2024).
  - MESES_INEXISTENTES: meses que não existem na fonte (ex.: jun/2024)
    são ignorados e não sinalizam o ano como incompleto.
  - Detecção de encoding por arquivo: utf-8 | cp1252 | latin-1 -> UTF-8.
  - Cabeçalho idêntico dentro do ano (assert), exceto 2020:
    jan/2020 tem coluna extra ("UF Placa", 23 vs 22 colunas) ->
    unificação via DuckDB union_by_name=true.
  - Delimitadores: 2018 = ',' ; 2019–2025 = ';'.
  - Validação obrigatória: soma das contagens por mês (DuckDB) ==
    contagem do arquivo final; colunas conferidas via DESCRIBE.
  - Apaga os ZIPs do ano e os temporários SOMENTE após validação.

Uso: .venv/bin/python scripts/02_extrair_unificar.py [ANO ...]
"""
import codecs
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path

import duckdb

DRIVE = Path("google_drive")
TMP = DRIVE / "_tmp"
OUT_DIR = Path("dados_brutos")
OUT_DIR.mkdir(exist_ok=True)

MESES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
         "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}

DELIM = {2018: ","}
DELIM_PADRAO = ";"

# Meses que NÃO EXISTEM na base original (confirmado pelo usuário) — não são
# pendência de ingestão e não devem sinalizar o ano como incompleto.
MESES_INEXISTENTES: dict[int, list[int]] = {
    2024: [6],   # junho/2024 não existe na fonte
}


# ---------- codecs ----------

def detectar_codec(path: Path) -> str:
    """utf-8 (com ou sem BOM) | cp1252 | latin-1 — por arquivo, streaming."""
    try:
        dec = codecs.getincrementaldecoder("utf-8")()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    break
                dec.decode(chunk)
            dec.decode(b"", final=True)
        return "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    break
                chunk.decode("cp1252")
        return "cp1252"
    except UnicodeDecodeError:
        return "latin-1"


def transcodificar(path: Path, codec: str) -> None:
    """Reescreve o arquivo em UTF-8 (no-place para cp1252/latin-1)."""
    if codec == "utf-8":
        return
    tmp = path.with_suffix(".utf8.tmp")
    with open(path, "rb") as fin, open(tmp, "wb") as fout:
        while True:
            chunk = fin.read(1 << 20)
            if not chunk:
                break
            fout.write(chunk.decode(codec).encode("utf-8"))
    tmp.replace(path)


def ler_header(path: Path) -> bytes:
    """Primeira linha (sem BOM, sem CR/LF final)."""
    with open(path, "rb") as f:
        line = f.readline()
    if line.startswith(codecs.BOM_UTF8):
        line = line[len(codecs.BOM_UTF8):]
    return line.rstrip(b"\r\n")


def sanear_aspas(path: Path) -> int:
    """Corrige linhas com número ÍMPAR de aspas (CSV malformado na origem).

    Padrão observado (unico na base): campo de modelo sem aspa de fechamento
    antes da quilometragem, ex.:
      ...;"VERSA 16 UNIQUE XXX;58197;"Desc...
    ->  ...;"VERSA 16 UNIQUE XXX";58197;"Desc...
    Retorna o nº de linhas corrigidas; aborta se nao convergir para par.
    """
    import re
    padrao = re.compile(rb'"([^";]+);(\d+);"')
    corrigidas = 0
    tmp = path.with_suffix(".fix.tmp")
    with open(path, "rb") as fin, open(tmp, "wb") as fout:
        for linha in fin:
            if linha.count(b'"') % 2 == 1:
                nova = padrao.sub(rb'"\1";\2;"', linha)
                if nova.count(b'"') % 2 == 1:
                    raise SystemExit(
                        f"[ERRO] linha com aspas ímpares irreparável em "
                        f"{path.name}: {linha[:300]!r}"
                    )
                fout.write(nova)
                corrigidas += 1
            else:
                fout.write(linha)
    tmp.replace(path)
    if corrigidas:
        print(f"  [SANIDADE] {path.name}: {corrigidas} linha(s) corrigida(s) de aspas ímpares")
    return corrigidas


# ---------- mapeamento zip -> meses ----------

def coletar_meses(ano: str) -> list[tuple[tuple[int, str], Path, str]]:
    """[(ordem, zip, member)] ordenado cronologicamente para o ano."""
    itens = []
    for z in sorted(DRIVE.glob("*.zip")):
        if not re.search(ano, z.name):
            continue
        with zipfile.ZipFile(z) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                nome = Path(info.filename).name.lower()
                m = re.search(r"_(\d{2})([a-z]?)\.csv$", nome)
                if m:
                    chave = (int(m.group(1)), m.group(2))
                elif nome[:-4] in MESES:
                    chave = (MESES[nome[:-4]], "")
                else:
                    raise SystemExit(f"[ERRO] nome não reconhecido: {info.filename} ({z.name})")
                itens.append((chave, z, info.filename))
    itens.sort(key=lambda t: t[0])
    return itens


def extrair(zip_path: Path, member: str, destino: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf, zf.open(member) as src, open(destino, "wb") as dst:
        shutil.copyfileobj(src, dst, 1 << 20)


# ---------- unificação ----------

def contar_duckdb(path: Path, delim: str) -> int:
    con = duckdb.connect()
    try:
        return con.execute(
            f"SELECT count(*) FROM read_csv('{path.resolve()}', header=true, "
            f"delim='{delim}', quote='\"', escape='\"', all_varchar=true, "
            "encoding='utf-8', strict_mode=false, parallel=false)"
        ).fetchone()[0]
    finally:
        con.close()


def garantir_newline(f):
    if f.tell() == 0:
        return
    f.seek(-1, 2)
    if f.read(1) != b"\n":
        f.seek(0, 2)
        f.write(b"\n")
    else:
        f.seek(0, 2)


def unificar_uniforme(ano: str, itens, delim: str, tmp_dir: Path) -> dict:
    """Concatenação com cabeçalho único (meses com cabeçalho idêntico)."""
    out = OUT_DIR / f"infracoes_{ano}.csv"
    meses_ok, linhas = [], 0
    header_base = None
    with open(out, "w+b") as fo:
        for idx, ((mes, suf), zpath, member) in enumerate(itens):
            tmp = tmp_dir / f"{ano}_{mes:02d}{suf}.csv"
            extrair(zpath, member, tmp)
            codec = detectar_codec(tmp)
            transcodificar(tmp, codec)
            sanear_aspas(tmp)
            hdr = ler_header(tmp)
            if idx == 0:
                header_base = hdr
                fo.write(hdr + b"\n")
            elif hdr != header_base:
                raise SystemExit(
                    f"[ERRO {ano}] cabeçalho divergente em mês {mes:02d}{suf}:\n"
                    f"  base: {header_base[:200]!r}\n"
                    f"  este: {hdr[:200]!r}"
                )
            n = contar_duckdb(tmp, delim)
            linhas += n
            with open(tmp, "rb") as fi:
                fi.readline()               # consome o cabeçalho
                shutil.copyfileobj(fi, fo, 1 << 20)
            garantir_newline(fo)
            meses_ok.append(f"{mes:02d}{suf}")
            tmp.unlink()
        n_cols = header_base.count(b";" if delim == ";" else b",") + 1

    n_out = contar_duckdb(out, delim)
    if n_out != linhas:
        raise SystemExit(f"[ERRO {ano}] entrada={linhas} != saida={n_out}")
    return {"arquivo": out, "registros": n_out, "meses": meses_ok,
            "cols": n_cols, "delim": delim}


def unificar_2020(itens, tmp_dir: Path) -> dict:
    """jan/2020 com coluna extra -> DuckDB union_by_name."""
    paths, headers = [], {}
    for (mes, suf), zpath, member in itens:
        tmp = tmp_dir / f"2020_{mes:02d}{suf}.csv"
        extrair(zpath, member, tmp)
        codec = detectar_codec(tmp)
        transcodificar(tmp, codec)
        sanear_aspas(tmp)
        headers[f"{mes:02d}{suf}"] = ler_header(tmp).decode("utf-8", "replace")
        paths.append(tmp)

    distintos = {}
    for k, h in headers.items():
        distintos.setdefault(h, []).append(k)
    print(f"  [2020] headers distintos: {len(distintos)}")
    if len(distintos) > 1:
        grupos = list(distintos.items())
        base_cols = grupos[0][0].split(";")
        for h, meses in grupos[1:]:
            outras = h.split(";")
            print(f"  [2020] {meses} vs {grupos[0][1]}: "
                  f"só_em_{meses[0]}={[c for c in outras if c not in base_cols]} | "
                  f"só_em_{grupos[0][1][0]}={[c for c in base_cols if c not in outras]}")

    linhas = sum(contar_duckdb(p, ";") for p in paths)
    out = OUT_DIR / "infracoes_2020.csv"
    con = duckdb.connect()
    try:
        file_list = ", ".join(f"'{p.resolve()}'" for p in paths)
        con.execute(
            f"COPY (SELECT * FROM read_csv([{file_list}], header=true, delim=';', "
            "quote='\"', escape='\"', all_varchar=true, encoding='utf-8', "
            "union_by_name=true, strict_mode=false)) "
            f"TO '{out.resolve()}' (HEADER, DELIMITER ';', QUOTE '\"')"
        )
        n_out = con.execute(
            f"SELECT count(*) FROM read_csv('{out.resolve()}', header=true, "
            "delim=';', quote='\"', escape='\"', all_varchar=true, "
            "encoding='utf-8', strict_mode=false)"
        ).fetchone()[0]
        n_cols = len(con.execute(
            f"DESCRIBE SELECT * FROM read_csv('{out.resolve()}', header=true, "
            "delim=';', quote='\"', escape='\"', all_varchar=true, "
            "encoding='utf-8', strict_mode=false)"
        ).fetchall())
    finally:
        con.close()
    for p in paths:
        p.unlink()
    if n_out != linhas:
        raise SystemExit(f"[ERRO 2020] entrada={linhas} != saida={n_out}")
    return {"arquivo": out, "registros": n_out,
            "meses": [f"{m:02d}{s}" for (m, s), _, _ in itens],
            "cols": n_cols, "delim": ";"}


# ---------- orquestração ----------

def processar_ano(ano: str) -> dict:
    itens = coletar_meses(ano)
    if not itens:
        raise SystemExit(f"[ERRO] nenhum mês encontrado para {ano} em google_drive/*.zip")

    presentes = sorted({m for (m, _), _, _ in itens})
    inexistentes = [m for m in MESES_INEXISTENTES.get(int(ano), []) if m not in presentes]
    esperados = [m for m in range(1, 13) if m not in inexistentes]
    faltando = [m for m in esperados if m not in presentes]
    if faltando:
        print(f"  [AVISO {ano}] MESES AUSENTES: {faltando} "
              f"(presentes: {[f'{m:02d}{s}' for (m, s), _, _ in itens]})")
    if inexistentes:
        print(f"  [INFO {ano}] mês(es) inexistente(s) na base (ignorado): "
              f"{inexistentes}")

    tmp_dir = TMP / ano
    tmp_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        if ano == "2020":
            res = unificar_2020(itens, tmp_dir)
        else:
            res = unificar_uniforme(ano, itens, DELIM.get(int(ano), DELIM_PADRAO), tmp_dir)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    dt = time.time() - t0
    mb = res["arquivo"].stat().st_size / 1e6
    print(f"OK {ano}: {res['registros']:,} registros | {len(res['meses'])} meses "
          f"| {res['cols']} colunas | delim='{res['delim']}' | "
          f"{res['arquivo'].name} ({mb:.1f} MB, {dt:.1f}s)")
    if faltando:
        print(f"   !! {ano} INCOMPLETO — falta(m) mês(es) {faltando} — "
              f"reenviar para o Drive antes do tratamento")

    # limpeza: só após validação
    zips_ano = [z for z in DRIVE.glob("*.zip") if re.search(ano, z.name)]
    for z in zips_ano:
        z.unlink()
    res["faltando"] = faltando
    res["zips_removidos"] = len(zips_ano)
    return res


def main(anos: list[str]):
    TMP.mkdir(parents=True, exist_ok=True)
    resumos = []
    for ano in anos:
        print(f"--- {ano} ---")
        resumos.append((ano, processar_ano(ano)))
    print("\n=== RESUMO ===")
    total = 0
    for ano, r in resumos:
        flag = "  <<<< INCOMPLETO" if r["faltando"] else ""
        print(f"  {ano}: {r['registros']:>12,} registros | {r['cols']} cols | "
              f"{r['arquivo'].name}{flag}")
        total += r["registros"]
    print(f"  TOTAL: {total:,} registros")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        anos = sys.argv[1:]
    else:
        anos = [str(y) for y in range(2018, 2026)]
    main(anos)
