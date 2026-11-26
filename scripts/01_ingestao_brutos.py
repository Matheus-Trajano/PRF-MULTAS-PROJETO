#!/usr/bin/env python3
"""
01 — Ingestão a partir de `dados_brutos/` (fonte única: `.csv.gz`, SEM Google Drive).

Os 19 CSVs anuais (2007–2025) já vivem versionados neste repositório,
compactados em gzip. Esta etapa é a porta de entrada da Fase 1 hoje: ela
**valida e ingere** direto desses arquivos — sem RAR, sem ZIP, sem Drive.

Por ano confere:
  1. o arquivo existe (`infracoes_<ANO>.csv.gz`);
  2. (opcional `--sha256`) o hash bate com `dados_brutos/SHA256SUMS.txt`;
  3. o DuckDB lê direto do gzip (`delim=';'`, `header`, `all_varchar`) e conta;
  4. a contagem bate com a tabela oficial (total 92.215.588);
  5. o cabeçalho é o schema canônico de 25 colunas, na ordem fixa.

Saída: relatório por ano (linhas, tamanho, status) + exit code 0/1.
Etapas seguintes: `03_normalizar.py` (opcional — os .gz já estão normalizados)
→ `04_tratar.py` (base analítica).

Uso:
  .venv/bin/python scripts/01_ingestao_brutos.py            # todos os 19 anos
  .venv/bin/python scripts/01_ingestao_brutos.py 2024 2025  # só os indicados
  .venv/bin/python scripts/01_ingestao_brutos.py --sha256   # + integridade dos .gz
"""
from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

import duckdb

BASE = Path(__file__).resolve().parent.parent
BRUTOS = BASE / "dados_brutos"
SUMS = BRUTOS / "SHA256SUMS.txt"

TOTAL_ESPERADO = 92_215_588

# Tabela oficial (dados_brutos/README.md) — contagem validada por ano
ESPERADO: dict[int, int] = {
    2007: 1_855_460, 2008: 2_432_797, 2009: 3_045_607, 2010: 3_038_357,
    2011: 2_884_305, 2012: 2_843_728, 2013: 3_251_800, 2014: 3_327_193,
    2015: 5_408_986, 2016: 5_584_915, 2017: 6_023_833, 2018: 7_356_159,
    2019: 5_742_110, 2020: 5_182_537, 2021: 5_241_299, 2022: 4_135_523,
    2023: 5_946_483, 2024: 8_710_022, 2025: 10_204_474,
}

# Schema canônico de 25 colunas (ordem fixa — igual ao 03_normalizar)
CANONICA = [
    "numero_auto", "data_infracao", "hora", "tip_abordagem",
    "ind_assinou_auto", "ind_veiculo_estrangeiro", "sentido_trafego",
    "uf_placa", "uf_infracao", "num_br_infracao", "num_km_infracao",
    "nom_municipio", "cod_infracao", "descricao_abreviada",
    "enquadramento", "data_inicio_vigencia", "data_fim_vigencia",
    "med_realizada", "med_considerada", "exc_verificado", "especie",
    "nome_veiculo_marca", "nom_modelo_veiculo", "tipo_veiculo",
    "qtd_infracoes",
]


def br(n: int) -> str:
    """Número no padrão brasileiro (ponto de milhar)."""
    return f"{n:,}".replace(",", ".")


def sha256_do_arquivo(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 22), b""):
            h.update(bloco)
    return h.hexdigest()


def hashes_esperados() -> dict[str, str]:
    """Lê dados_brutos/SHA256SUMS.txt → {nome_do_arquivo: hash}."""
    if not SUMS.exists():
        raise SystemExit(f"[ERRO] {SUMS} não encontrado (necessário p/ --sha256)")
    d = {}
    for linha in SUMS.read_text(encoding="utf-8").splitlines():
        partes = linha.split()
        if len(partes) >= 2:
            d[partes[-1]] = partes[0].lower()
    return d


def validar_ano(con: duckdb.DuckDBPyConnection, ano: int,
                esperado_sha: dict[str, str] | None) -> tuple[bool, str, int]:
    """Valida um ano. Retorna (ok, motivo_do_erro_ou_vazio, linhas)."""
    arq = BRUTOS / f"infracoes_{ano}.csv.gz"
    if not arq.exists():
        return False, "arquivo ausente", 0

    if esperado_sha is not None:
        hash_esp = esperado_sha.get(arq.name)
        if hash_esp is None:
            return False, f"{arq.name} fora do SHA256SUMS.txt", 0
        if sha256_do_arquivo(arq) != hash_esp:
            return False, "sha256 divergente", 0

    # Mesmas opções do 04_tratar (strict_mode=false + quote/escape
    # explícitos) — o reader padrão recusa linhas de 2022/2024.
    q = chr(34)
    base_opts = (
        "header=true, delim=';', all_varchar=true, strict_mode=false, "
        + "quote='" + q + "', escape='" + q + "'"
    )
    cols: list[str] = []
    n = 0
    for paralelo in (True, False):
        opts = base_opts + ", parallel=" + ("true" if paralelo else "false")
        try:
            n = con.execute(
                f"SELECT COUNT(*) FROM read_csv('{arq}', {opts})"
            ).fetchone()[0]
            cols = [r[0] for r in con.execute(
                f"DESCRIBE SELECT * FROM read_csv('{arq}', {opts})"
            ).fetchall()]
            break
        except duckdb.NotImplementedException:
            continue  # reader paralelo recusou → tenta serial (caso 2023)
        except Exception as exc:  # erro real de parsing
            return False, f"leitura falhou: {str(exc)[:80]}", 0
    else:
        return False, "leitura falhou (paralelo e serial)", 0

    if n != ESPERADO[ano]:
        return False, f"{br(n)} linhas != {br(ESPERADO[ano])} esperadas", n
    if cols != CANONICA:
        return False, f"header != canônico ({len(cols)} col vs 25)", n
    return True, "", n


def main(argv: list[str]) -> int:
    anos = [int(a) for a in argv if a.isdigit()]
    checar_sha = "--sha256" in argv
    if not anos:
        anos = sorted(ESPERADO)

    t0 = time.time()
    con = duckdb.connect(config={"threads": "2", "memory_limit": "1500MB"})
    esperado_sha = hashes_esperados() if checar_sha else None

    print("=" * 78)
    print("INGESTÃO — fonte: dados_brutos/*.csv.gz (sem Google Drive)")
    print(f"  anos: {min(anos)}–{max(anos)} · sha256: {'sim' if checar_sha else 'não'}")
    print("=" * 78)
    print(f"  {'ANO':>4}  {'TAMANHO':>10}  {'LINHAS':>13}  {'ESPERADO':>13}  STATUS")

    falhas: list[str] = []
    total = 0
    for ano in anos:
        arq = BRUTOS / f"infracoes_{ano}.csv.gz"
        ok, motivo, n = validar_ano(con, ano, esperado_sha)
        total += n
        tam = f"{arq.stat().st_size / 1e6:.1f} MB" if arq.exists() else "—"
        status = "OK" if ok else f"FALHA — {motivo}"
        print(f"  {ano:>4}  {tam:>10}  {br(n):>13}  "
              f"{br(ESPERADO[ano]):>13}  {status}")
        if not ok:
            falhas.append(f"{ano}: {motivo}")

    print("-" * 78)
    if len(anos) == len(ESPERADO):
        print(f"  {'TOTAL':>4}  {'':>10}  {br(total):>13}  "
              f"{br(TOTAL_ESPERADO):>13}  {'OK' if total == TOTAL_ESPERADO else 'FALHA'}")
        if total != TOTAL_ESPERADO:
            falhas.append(f"total {br(total)} != {br(TOTAL_ESPERADO)}")

    if falhas:
        print(f"\n[ERRO] ingestão com {len(falhas)} falha(s):")
        for f in falhas:
            print(f"  - {f}")
        return 1

    print(f"\nINGESTAO_OK — {len(anos)}/19 anos validados a partir de "
          f"dados_brutos/*.csv.gz ({time.time() - t0:.0f}s, sem Google Drive)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
