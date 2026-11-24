#!/usr/bin/env python3
"""
01 — Ingestão: unifica os CSVs mensais/bimestrais de cada ano
em UM arquivo por ano (dados_brutos/infracoes_<ANO>.csv).

Motor: DuckDB (import duckdb) — leitura e escrita via SQL.
Regras:
  - Ordem cronológica explícita dos arquivos (jan..dez / bimestres).
  - all_varchar=true: só une, não infere tipos (tratamento vem depois).
  - Validação: contagem de linhas de entrada == saída.
  - Cabeçalho idêntico dentro do ano (assert).
"""
import hashlib
import sys
import time
from pathlib import Path

import duckdb

EXTRACTED = Path("google_drive/_extracted")
OUT_DIR = Path("dados_brutos")
OUT_DIR.mkdir(exist_ok=True)

MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]
BIMESTRES = ["jan_fev", "mar_abr", "mai_jun", "jul_ago", "set_out", "nov_dez"]


def ordenar_arquivos(year_dir: Path) -> list[Path]:
    stems = {p.stem for p in year_dir.glob("*.csv")}
    if len(stems) == 12 and all(m in stems for m in MESES):
        return [year_dir / f"{m}.csv" for m in MESES]
    if len(stems) == 6 and all(b in stems for b in BIMESTRES):
        return [year_dir / f"{b}.csv" for b in BIMESTRES]
    raise SystemExit(f"[ERRO] Padrão de arquivos não reconhecido em {year_dir}: {sorted(stems)}")


def detectar_encoding(files: list[Path]) -> str:
    """Detecta a encoding do ano: utf-8 se todos decodificam, senao latin-1."""
    for f in files:
        raw = f.read_bytes()
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            return "latin-1"
    return "utf-8"


def header_hash(path: Path) -> str:
    with open(path, "rb") as fh:
        return hashlib.md5(fh.readline()).hexdigest()


def unificar_ano(year: str) -> dict:
    year_dir = EXTRACTED / year
    files = ordenar_arquivos(year_dir)

    # assert: cabeçalho idêntico em todos os arquivos do ano
    hashes = {header_hash(f) for f in files}
    if len(hashes) != 1:
        raise SystemExit(f"[ERRO] Cabeçalhos divergentes em {year}: {hashes}")

    enc = detectar_encoding(files)
    out = OUT_DIR / f"infracoes_{year}.csv"
    con = duckdb.connect()
    try:
        file_list = ", ".join(f"'{f.resolve()}'" for f in files)
        # contagem de entrada (registros, sem cabeçalho)
        n_in = con.execute(
            f"SELECT count(*) FROM read_csv([{file_list}], "
            f"header=true, delim=',', all_varchar=true, encoding='{enc}')"
        ).fetchone()[0]

        t0 = time.time()
        con.execute(
            f"COPY (SELECT * FROM read_csv([{file_list}], "
            f"header=true, delim=',', all_varchar=true, encoding='{enc}')) "
            f"TO '{out.resolve()}' (HEADER, DELIMITER ',', QUOTE '\"')"
        )
        dt = time.time() - t0

        n_out = con.execute(
            f"SELECT count(*) FROM read_csv('{out.resolve()}', "
            "header=true, delim=',', all_varchar=true)"
        ).fetchone()[0]

        if n_in != n_out:
            raise SystemExit(f"[ERRO] {year}: entrada={n_in} != saida={n_out}")

        size_mb = out.stat().st_size / 1e6
        print(f"OK {year}: {n_out:,} registros | {len(files)} arquivos -> "
              f"{out.name} ({size_mb:.1f} MB, {dt:.1f}s)")
        return {"ano": year, "registros": n_out, "arquivos": len(files),
                "mb": round(size_mb, 1), "segundos": round(dt, 1)}
    finally:
        con.close()


def main(anos: list[str]):
    resumo = []
    for year in anos:
        resumo.append(unificar_ano(year))
    print("\n=== RESUMO ===")
    total = sum(r["registros"] for r in resumo)
    for r in resumo:
        print(f"  {r['ano']}: {r['registros']:>10,} registros  ({r['mb']} MB)")
    print(f"  TOTAL: {total:,} registros")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        anos = sys.argv[1:]
    else:
        anos = sorted(d.name for d in EXTRACTED.iterdir() if d.is_dir())
    main(anos)
