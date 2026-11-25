#!/usr/bin/env python3
"""
05_enriquecer.py — Etapa A: colunas derivadas para visualizacao (38 colunas).

Le dados_tratados/base_analitica/*.parquet (28 col) e regrava com +9 colunas:

  SEMANA_DO_MES    SMALLINT  1..5  = ((dia_do_mes - 1) / 7) + 1
  DIA_SEMANA       VARCHAR   SEGUNDA..DOMINGO (ASCII, regra da base)
  DIA_SEMANA_NUM   SMALLINT  1=SEGUNDA .. 7=DOMINGO
  FIM_DE_SEMANA    VARCHAR   SIM | NAO
  TURNO            VARCHAR   MADRUGADA(0-5) MANHA(6-11) TARDE(12-17) NOITE(18-23);
                             NULL quando HORA e NULL (exibir como NAO INFORMADO)
  FAIXA_HORARIA    VARCHAR   00-05 | 06-11 | 12-17 | 18-23; NULL com HORA NULL
  BR_FORMATADA     VARCHAR   BR-040 (lpad 3); NULL quando NUM_BR NULL
  CHAVE_LOCALIDADE VARCHAR   UF_INFRACAO|NOM_MUNICIPIO (resolve 114 homonimos)
  NATUREZA_INFRA   VARCHAR   agrupador heuristico v1 (palavra-chave em
                             DESCRICAO_ABRVIADA+ENQUADRAMENTO): VELOCIDADE,
                             DOCUMENTACAO, ALCOOL_DROGAS, TRANSITO, SEGURANCA,
                             ESTACIONAMENTO, VEICULO_EQUIPAMENTO, OUTRAS

Saneamentos:
  NUM_KM_INFRACAO > 5000 (outlier)      -> NULL
  NUM_BR_INFRACAO fora de 1..999        -> NULL

Validacao: por ano contagem in==out + dominios + coerencias; total 92.215.588.
Uso: .venv/bin/python scripts/05_enriquecer.py [ANO ...]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
BASE = RAIZ / "dados_tratados" / "base_analitica"
TMP_DIR = RAIZ / "dados_tratados" / "_ddb_tmp"
VALIDACAO = RAIZ / "dados_tratados" / "_enriquecimento.jsonl"
TOTAL_ESPERADO = 92_215_588

DIAS = ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA", "SABADO", "DOMINGO"]

# --- SQL ------------------------------------------------------------------
# nivel 1: le parquet + auxiliar _d (texto para classificar natureza)
# nivel 2: 28 colunas originais (KM/BR saneados) + 9 derivadas
SQL = """
WITH src AS (
    SELECT *,
           upper(coalesce(DESCRICAO_ABRVIADA, '') || ' ' || coalesce(ENQUADRAMENTO, '')) AS _d
    FROM read_parquet('{arquivo}')
)
SELECT
    NUMERO_AUTO, DATA_INFRACAO, HORA, TIP_ABORDAGEM, IND_ASSINOU_AUTO,
    IND_VEICULO_ESTRANGEIRO, SENTIDO_TRAFEGO, UF_PLACA, UF_INFRACAO,
    NUM_BR_INFRACAO,
    CASE WHEN NUM_KM_INFRACAO > 5000 THEN NULL ELSE NUM_KM_INFRACAO END AS NUM_KM_INFRACAO,
    NOM_MUNICIPIO, COD_INFRACAO, DESCRICAO_ABRVIADA, ENQUADRAMENTO,
    DATA_INICIO_VIGENCIA, DATA_FIM_VIGENCIA, MED_REALIZADA, MED_CONSIDERADA,
    EXC_VERIFICADO, ESPECIE, NOME_VEICULO_MARCA, NOM_MODELO_VEICULO,
    TIPO_VEICULO, QTD_INFRACOES,
    MES, ANO, QUARTIL,
    -- derivadas temporais
    ((day(DATA_INFRACAO) - 1) / 7 + 1)::SMALLINT AS SEMANA_DO_MES,
    CASE dayname(DATA_INFRACAO)
        WHEN 'Monday' THEN 'SEGUNDA'   WHEN 'Tuesday' THEN 'TERCA'
        WHEN 'Wednesday' THEN 'QUARTA' WHEN 'Thursday' THEN 'QUINTA'
        WHEN 'Friday' THEN 'SEXTA'     WHEN 'Saturday' THEN 'SABADO'
        WHEN 'Sunday' THEN 'DOMINGO' END AS DIA_SEMANA,
    CASE dayname(DATA_INFRACAO)
        WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3
        WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6
        WHEN 'Sunday' THEN 7 END::SMALLINT AS DIA_SEMANA_NUM,
    CASE WHEN DATA_INFRACAO IS NULL THEN NULL
         WHEN dayname(DATA_INFRACAO) IN ('Saturday', 'Sunday') THEN 'SIM'
         ELSE 'NAO' END AS FIM_DE_SEMANA,
    CASE
        WHEN HORA IS NULL THEN NULL
        WHEN hour(HORA) < 6  THEN 'MADRUGADA'
        WHEN hour(HORA) < 12 THEN 'MANHA'
        WHEN hour(HORA) < 18 THEN 'TARDE'
        ELSE 'NOITE' END AS TURNO,
    CASE
        WHEN HORA IS NULL THEN NULL
        WHEN hour(HORA) < 6  THEN '00-05'
        WHEN hour(HORA) < 12 THEN '06-11'
        WHEN hour(HORA) < 18 THEN '12-17'
        ELSE '18-23' END AS FAIXA_HORARIA,
    -- derivadas geograficas / veiculo / infração
    CASE WHEN NUM_BR_INFRACAO IS NULL THEN NULL
         ELSE 'BR-' || lpad(NUM_BR_INFRACAO::VARCHAR, 3, '0') END AS BR_FORMATADA,
    CASE WHEN UF_INFRACAO IS NULL OR NOM_MUNICIPIO IS NULL THEN NULL
         ELSE UF_INFRACAO || '|' || NOM_MUNICIPIO END AS CHAVE_LOCALIDADE,
    CASE
        WHEN _d = ' ' THEN NULL
        WHEN _d LIKE '%VELOCIDAD%' THEN 'VELOCIDADE'
        WHEN _d LIKE '%ALCOOL%' OR _d LIKE '%DROGA%' OR _d LIKE '%PRONTEZ%'
              OR _d LIKE '%RECUSA%' OR _d LIKE '%TOXICO%' THEN 'ALCOOL_DROGAS'
        WHEN _d LIKE '%DOCUMENT%' OR _d LIKE '%CNH%' OR _d LIKE '%RENAVAM%'
              OR _d LIKE '%LICENCIAMENT%' OR _d LIKE '%PERMISS%'
              OR _d LIKE '%CATEGORI%' THEN 'DOCUMENTACAO'
        WHEN _d LIKE '%SEMAFOR%' OR _d LIKE '%SINAL%' OR _d LIKE '%PARE%'
              OR _d LIKE '%FAIXA%' OR _d LIKE '%PEDESTRE%' OR _d LIKE '%CIRCULACAO%'
              OR _d LIKE '%CONTRA MAO%' OR _d LIKE '%SENTIDO%' THEN 'TRANSITO'
        WHEN _d LIKE '%CINTO%' OR _d LIKE '%CAPACETE%' OR _d LIKE '%CRIANCA%'
              OR _d LIKE '%BEBE%' THEN 'SEGURANCA'
        WHEN _d LIKE '%ESTACIONA%' OR _d LIKE '%VAGA%' THEN 'ESTACIONAMENTO'
        WHEN _d LIKE '%FAROL%' OR _d LIKE '%LANTERNA%' OR _d LIKE '%PNEU%'
              OR _d LIKE '%ESPELHO%' OR _d LIKE '%PLACA%' OR _d LIKE '%INSPECAO%'
              OR _d LIKE '%EQUIPAMENTO%' OR _d LIKE '%LIMPEZA%' OR _d LIKE '%SOM%'
              OR _d LIKE '%DESCARGA%' OR _d LIKE '%EMISSAO%' THEN 'VEICULO_EQUIPAMENTO'
        ELSE 'OUTRAS' END AS NATUREZA_INFRA
FROM src
"""

SQL_VALIDACAO = """
SELECT
    count(*)                                                          AS linhas,
    count(*) FILTER (WHERE DATA_INFRACAO IS NOT NULL
                     AND (SEMANA_DO_MES IS NULL OR SEMANA_DO_MES NOT BETWEEN 1 AND 5)) AS semana_ruim,
    count(*) FILTER (WHERE DATA_INFRACAO IS NOT NULL
                     AND (DIA_SEMANA IS NULL OR DIA_SEMANA NOT IN ({dias})))          AS dia_ruim,
    count(*) FILTER (WHERE (HORA IS NULL) <> (TURNO IS NULL))          AS turno_incoerente,
    count(*) FILTER (WHERE DIA_SEMANA IS NOT NULL
                     AND FIM_DE_SEMANA <> CASE WHEN DIA_SEMANA IN ('SABADO','DOMINGO')
                                               THEN 'SIM' ELSE 'NAO' END)             AS fim_incoerente,
    count(*) FILTER (WHERE (NUM_BR_INFRACAO IS NULL) <> (BR_FORMATADA IS NULL)
                     OR (BR_FORMATADA IS NOT NULL
                         AND BR_FORMATADA <> 'BR-' || lpad(NUM_BR_INFRACAO::VARCHAR,3,'0'))) AS brfmt_ruim,
    count(*) FILTER (WHERE (UF_INFRACAO IS NULL OR NOM_MUNICIPIO IS NULL)
                          <> (CHAVE_LOCALIDADE IS NULL))               AS chave_ruim,
    count(*) FILTER (WHERE NUM_KM_INFRACAO > 5000)                     AS km_outlier_resto,
    count(DISTINCT NATUREZA_INFRA)                                     AS n_naturezas
FROM read_parquet('{destino}')
"""

SQL_ENTRADA = """
SELECT
    count(*) FILTER (WHERE NUM_KM_INFRACAO > 5000) AS km_outliers,
    count(*) FILTER (WHERE NUM_BR_INFRACAO IS NOT NULL
                     AND (NUM_BR_INFRACAO < 1 OR NUM_BR_INFRACAO > 999)) AS br_fora_faixa
FROM read_parquet('{arquivo}')
"""


def enriquecer_ano(con: duckdb.DuckDBPyConnection, ano: int) -> dict:
    arquivo = BASE / f"infracoes_{ano}.parquet"
    if not arquivo.exists():
        raise FileNotFoundError(arquivo)
    destino = arquivo.with_suffix(".novo.parquet")
    destino.unlink(missing_ok=True)

    ent = con.execute(SQL_ENTRADA.format(arquivo=arquivo)).fetchone()
    con.execute(
        f"COPY ({SQL.format(arquivo=arquivo)}) TO '{destino}' "
        f"(FORMAT PARQUET, COMPRESSION 'ZSTD')"
    )
    dias_sql = ", ".join(f"'{d}'" for d in DIAS)
    val = con.execute(
        SQL_VALIDACAO.format(destino=destino, dias=dias_sql)
    ).fetchone()
    if val[0] != ent_total(con, arquivo):
        raise AssertionError(f"[{ano}] contagem divergente")
    for idx, nome in ((1, "semana_ruim"), (2, "dia_ruim"), (3, "turno_incoerente"),
                      (4, "fim_incoerente"), (5, "brfmt_ruim"), (6, "chave_ruim"),
                      (7, "km_outlier_resto")):
        if val[idx] != 0:
            raise AssertionError(f"[{ano}] {nome}={val[idx]} (esperado 0)")

    arquivo.unlink()
    destino.rename(arquivo)
    return {
        "ano": ano, "linhas": val[0],
        "km_outliers_corrigidos": ent[0], "br_fora_faixa_corrigidos": ent[1],
        "n_naturezas": val[8],
        "parquet_mb": round(arquivo.stat().st_size / 1e6, 1),
    }


def ent_total(con: duckdb.DuckDBPyConnection, arquivo: Path) -> int:
    return con.execute(f"SELECT count(*) FROM read_parquet('{arquivo}')").fetchone()[0]


def main() -> None:
    anos = [int(a) for a in sys.argv[1:] if a.isdigit()] or list(range(2007, 2026))
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    if len(anos) == 19:
        VALIDACAO.unlink(missing_ok=True)

    con = duckdb.connect()
    con.execute("SET threads=2")
    con.execute("SET memory_limit='2400MB'")
    con.execute(f"SET temp_directory='{TMP_DIR}'")
    con.execute("SET preserve_insertion_order=false")

    t0 = time.time()
    total = 0
    for ano in anos:
        ta = time.time()
        m = enriquecer_ano(con, ano)
        total += m["linhas"]
        with VALIDACAO.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(m, ensure_ascii=False) + "\n")
        print(f"[{ano}] {m['linhas']:,} linhas -> {m['parquet_mb']} MB "
              f"({time.time()-ta:.0f}s) | km_out={m['km_outliers_corrigidos']} "
              f"br_ruim={m['br_fora_faixa_corrigidos']} naturezas={m['n_naturezas']}",
              flush=True)

    print(f"OK {len(anos)} anos, {total:,} linhas, {time.time()-t0:.0f}s", flush=True)
    if len(anos) == 19 and total != TOTAL_ESPERADO:
        raise SystemExit(f"TOTAL {total} != {TOTAL_ESPERADO}")


if __name__ == "__main__":
    main()
