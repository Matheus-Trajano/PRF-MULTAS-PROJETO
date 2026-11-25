#!/usr/bin/env python3
"""
Etapa 03 — Normalização dos CSVs unificados de `dados_brutos`.

Padroniza TODOS os anos (2007–2025) para um schema canônico único:

  * 25 colunas canônicas (união dos schemas das três eras), ordem fixa,
    nomes em snake_case
  * Delimitador único `;`, UTF-8, LF, sem BOM, aspas mínimas
  * Datas em AAAA-MM-DD (converte DD/MM/AAAA se aparecer; já é o padrão)
  * `hora` em HH:MM:SS (anos que só tinham o dígito da hora → 'HH:00:00')
  * TRIM em todos os campos
  * Tokens de ausência ('NA', 'N/I', 'N/A' e vazio) → vazio (NULL)

Validação por ano (obrigatória): contagem de entrada == contagem de saída,
`data_infracao` 100% ISO e `hora` 100% HH:MM:SS no arquivo normalizado.
Só depois disso o temporário substitui o arquivo final.

Aceita fonte `.csv` ou `.csv.gz` (a etapa de compactação prévia libera disco).
Saída: sobrescreve `dados_brutos/infracoes_<ANO>.csv` (via `.norm.csv` + replace).

Uso:
  .venv/bin/python scripts/03_normalizar.py              # todos os anos
  .venv/bin/python scripts/03_normalizar.py 2007 2008    # só os indicados
"""
from __future__ import annotations

import csv
import gzip
import os
import shutil
import sys
import time
import unicodedata
from pathlib import Path

import duckdb

BASE = Path(__file__).resolve().parent.parent
BRUTOS = BASE / "dados_brutos"

# ---------------------------------------------------------------------------
# Schema canônico (união de todas as eras, ordem fixa)
# ---------------------------------------------------------------------------
CANONICA = [
    "numero_auto",           # era2/3 (2019+)            — era1: ausente
    "data_infracao",         # era1: dat_infracao
    "hora",                  # era1 2015+                — 2007–2014: ausente
    "tip_abordagem",
    "ind_assinou_auto",
    "ind_veiculo_estrangeiro",
    "sentido_trafego",       # era1: ind_sentido_trafego
    "uf_placa",              # 2021: ausente
    "uf_infracao",
    "num_br_infracao",
    "num_km_infracao",
    "nom_municipio",
    "cod_infracao",          # era1 2017+                — 2007–2016: ausente
    "descricao_abreviada",
    "enquadramento",
    "data_inicio_vigencia",
    "data_fim_vigencia",
    "med_realizada",         # era2/3: Medição Infração
    "med_considerada",
    "exc_verificado",
    "especie",
    "nome_veiculo_marca",
    "nom_modelo_veiculo",    # era2 2019–2021: ausente
    "tipo_veiculo",          # só era3 (2022+)
    "qtd_infracoes",         # era2 2020+ / era3
]

DATAS = {"data_infracao", "data_inicio_vigencia", "data_fim_vigencia"}
TOKENS_AUSENCIA = ("", "NA", "N/I", "N/A")


def _n(nome: str) -> str:
    """Normaliza nome de coluna: sem acento, minúsculo, sem espaços extras."""
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


# Mapeia nome-de-coluna-normalizado -> coluna canônica (inclui identidade p/ re-execução)
MAPEAMENTO: dict[str, str] = {c: c for c in CANONICA}
MAPEAMENTO.update({
    # era 1 (2007–2018, snake_case)
    "dat_infracao": "data_infracao",
    "ind_sentido_trafego": "sentido_trafego",
    # era 2/3 (2019–2025, pt-BR)
    "numero do auto": "numero_auto",
    "data da infracao (dd/mm/aaaa)": "data_infracao",
    "indicador de abordagem": "tip_abordagem",
    "assinatura do auto": "ind_assinou_auto",
    "indicador veiculo estrangeiro": "ind_veiculo_estrangeiro",
    "sentido trafego": "sentido_trafego",
    "uf placa": "uf_placa",
    "uf infracao": "uf_infracao",
    "br infracao": "num_br_infracao",
    "km infracao": "num_km_infracao",
    "municipio": "nom_municipio",
    "codigo da infracao": "cod_infracao",
    "descricao abreviada infracao": "descricao_abreviada",
    "enquadramento da infracao": "enquadramento",
    "inicio vigencia da infracao": "data_inicio_vigencia",
    "fim vigencia infracao": "data_fim_vigencia",
    "medicao infracao": "med_realizada",
    "medicao considerada": "med_considerada",
    "excesso verificado": "exc_verificado",
    "descricao especie veiculo": "especie",
    "descricao marca veiculo": "nome_veiculo_marca",
    "descricao modelo veiculo": "nom_modelo_veiculo",
    "descricao tipo veiculo": "tipo_veiculo",
    "hora infracao": "hora",
    "qtd infracoes": "qtd_infracoes",
})


def _q(ident: str) -> str:
    return '"' + ident.replace('"', '""') + '"'


def _expr_data(q: str) -> str:
    in_list = ", ".join(f"'{t}'" for t in TOKENS_AUSENCIA)
    return (
        f"CASE WHEN trim({q}) IN ({in_list}) THEN NULL "
        f"WHEN regexp_matches(trim({q}), '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$') THEN trim({q}) "
        f"WHEN regexp_matches(trim({q}), '^[0-9]{{2}}/[0-9]{{2}}/[0-9]{{4}}$') "
        f"THEN substr(trim({q}), 7, 4) || '-' || substr(trim({q}), 4, 2) || '-' || substr(trim({q}), 1, 2) "
        f"ELSE trim({q}) END"
    )


def _expr_hora(q: str) -> str:
    in_list = ", ".join(f"'{t}'" for t in TOKENS_AUSENCIA)
    return (
        f"CASE WHEN trim({q}) IN ({in_list}) THEN NULL "
        f"WHEN regexp_matches(trim({q}), '^[0-9]{{2}}:[0-9]{{2}}:[0-9]{{2}}$') THEN trim({q}) "
        f"WHEN regexp_matches(trim({q}), '^[0-9]{{1,2}}$') "
        f"AND try_cast(trim({q}) AS INTEGER) BETWEEN 0 AND 23 "
        f"THEN lpad(trim({q}), 2, '0') || ':00:00' "
        f"ELSE trim({q}) END"
    )


def _expr_comum(q: str) -> str:
    in_list = ", ".join(f"'{t}'" for t in TOKENS_AUSENCIA)
    return f"CASE WHEN trim({q}) IN ({in_list}) THEN NULL ELSE trim({q}) END"


def _fonte(ano: int) -> Path:
    gz = BRUTOS / f"infracoes_{ano}.csv.gz"
    csv_p = BRUTOS / f"infracoes_{ano}.csv"
    if gz.exists():
        return gz
    if csv_p.exists():
        return csv_p
    raise SystemExit(f"[ERRO] fonte não encontrada para {ano} ({csv_p.name} / {gz.name})")


def _ler_cabecalho(src: Path) -> tuple[list[str], str]:
    opener = gzip.open if src.suffix == ".gz" else open
    with opener(src, "rb") as fh:
        cab = fh.readline().decode("utf-8", "replace").rstrip("\r\n")
    # delim detectado pelo próprio cabeçalho (funciona também p/ re-execução)
    delim = ";" if ";" in cab else ","
    cols = next(csv.reader([cab], delimiter=delim))
    return cols, delim


def normalizar_ano(ano: int) -> tuple[int, float]:
    src = _fonte(ano)
    dst = BRUTOS / f"infracoes_{ano}.csv"
    tmp = dst.with_name(f"infracoes_{ano}.norm.csv")
    if tmp.exists():
        tmp.unlink()

    cols, delim = _ler_cabecalho(src)

    # ---- monta o SELECT no schema canônico -------------------------------
    origem: dict[str, str] = {}
    desconhecidas: list[str] = []
    for c in cols:
        chave = _n(c)
        if chave not in MAPEAMENTO:
            desconhecidas.append(c)
            continue
        alvo = MAPEAMENTO[chave]
        if alvo in origem:
            raise SystemExit(
                f"[ERRO] {ano}: duas colunas de origem mapeiam para '{alvo}': "
                f"'{origem[alvo]}' e '{c}'"
            )
        origem[alvo] = c
    if desconhecidas:
        raise SystemExit(f"[ERRO] {ano}: colunas de origem sem mapeamento: {desconhecidas}")

    partes: list[str] = []
    for alvo in CANONICA:
        if alvo not in origem:
            partes.append(f'CAST(NULL AS VARCHAR) AS "{alvo}"')
            continue
        q = _q(origem[alvo])
        if alvo in DATAS:
            e = _expr_data(q)
        elif alvo == "hora":
            e = _expr_hora(q)
        else:
            e = _expr_comum(q)
        partes.append(f'{e} AS "{alvo}"')
    selecao = ", ".join(partes)

    con = duckdb.connect()
    # tuning p/ máquina pequena (2 cores / 3,8 GB): 1 thread + sem buffer de
    # ordenação (com 1 thread a ordem de origem é preservada) + spill em disco
    (BRUTOS / "_ddb_tmp").mkdir(exist_ok=True)
    con.execute("SET threads=1")
    con.execute("SET preserve_insertion_order=false")
    con.execute("SET memory_limit='2400MB'")
    con.execute(f"SET temp_directory='{BRUTOS / '_ddb_tmp'}'")
    caminho = str(src.resolve())
    leitura = (
        f"read_csv('{caminho}', header=true, delim='{delim}', quote='\"', escape='\"', "
        "all_varchar=true, encoding='utf-8', strict_mode=false, parallel=true)"
    )

    t0 = time.time()
    try:
        n_in = con.execute(f"SELECT count(*) FROM {leitura}").fetchone()[0]
    except duckdb.NotImplementedException:
        # alguns arquivos nao suportam o CSV reader paralelo ("full read");
        # cai para leitura serial (bufferiza o descompactado — só viável com
        # arquivos < limite de memória do DuckDB)
        leitura = (
            f"read_csv('{caminho}', header=true, delim='{delim}', quote='\"', escape='\"', "
            "all_varchar=true, encoding='utf-8', strict_mode=false, parallel=false)"
        )
        print(f"  [INFO {ano}] reader paralelo indisponível — usando leitura serial")
        n_in = con.execute(f"SELECT count(*) FROM {leitura}").fetchone()[0]

    con.execute(
        f"COPY (SELECT {selecao} FROM {leitura}) TO '{tmp.resolve()}' "
        "(HEADER true, DELIMITER ';', QUOTE '\"', ESCAPE '\"', NULL '')"
    )

    leitura_tmp = (
        f"read_csv('{tmp.resolve()}', header=true, delim=';', quote='\"', escape='\"', "
        "all_varchar=true, encoding='utf-8', strict_mode=false, parallel=true)"
    )
    n_out, bad_data, bad_hora = con.execute(
        f"SELECT count(*), "
        f"coalesce(sum(CASE WHEN data_infracao IS NOT NULL AND data_infracao <> '' "
        f"AND NOT regexp_matches(data_infracao, '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$') "
        f"THEN 1 ELSE 0 END), 0), "
        f"coalesce(sum(CASE WHEN hora IS NOT NULL AND hora <> '' "
        f"AND NOT regexp_matches(hora, '^[0-9]{{2}}:[0-9]{{2}}:[0-9]{{2}}$') "
        f"THEN 1 ELSE 0 END), 0) "
        f"FROM {leitura_tmp}"
    ).fetchone()
    con.close()

    if n_in != n_out:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"[ERRO] {ano}: contagem divergente — entrada {n_in:,} vs saída {n_out:,}")
    if bad_data or bad_hora:
        tmp.unlink(missing_ok=True)
        raise SystemExit(
            f"[ERRO] {ano}: valores fora do padrão no normalizado — "
            f"data_infracao={bad_data}, hora={bad_hora}"
        )

    # ---- troca definitiva -----------------------------------------------
    os.replace(tmp, dst)
    if src != dst:            # remove o .gz depois da troca validada
        src.unlink()

    dt = time.time() - t0
    mb = dst.stat().st_size / 1e6
    ausentes = [c for c in CANONICA if c not in origem]
    info = f" | ausentes(vazio): {', '.join(ausentes)}" if ausentes else ""
    print(
        f"OK {ano}: {n_out:,} registros | 25 colunas | delim=';' | "
        f"{dst.name} ({mb:,.1f} MB, {dt:.1f}s){info}",
        flush=True,
    )
    livre = shutil.disk_usage(BRUTOS).free / 1e9
    print(f"     disco livre: {livre:.2f} GB", flush=True)
    return n_out, dt


def main(argv: list[str]) -> int:
    if argv:
        anos = [int(a) for a in argv]
    else:
        anos = sorted(
            int(p.stem.split("_")[1].split(".")[0])
            for p in BRUTOS.glob("infracoes_*.csv*")
            if not p.name.endswith(".norm.csv")
        )
    total = 0
    t0 = time.time()
    for ano in anos:
        n, _ = normalizar_ano(ano)
        total += n
    print(f"\n=== RESUMO NORMALIZAÇÃO ===")
    print(f"  anos: {min(anos)}–{max(anos)} ({len(anos)} arquivos)")
    print(f"  registros: {total:,}")
    print(f"  tempo total: {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
