#!/usr/bin/env python3
"""
06_agregar.py — Etapa B: camada de agregados pre-computados para os graficos.

Le dados_tratados/base_analitica/*.parquet (37 col, Etapa A) e grava
dados_tratados/agregados/*.parquet — 13 tabelas por granularidade, todas com
metrica `qtd` (count(*)) e dimensao ANO+UF_INFRACAO p/ filtros globais.
Cada agregado varre os parquets direto (sem temp table — o spill materialize
estourou o disco):

  tempo_diario         DATA_INFRACAO | ANO MES QUARTIL SEMANA_DO_MES
                             DIA_SEMANA(_NUM) FIM_DE_SEMANA            ~7k
  hora_diaria          DATA_INFRACAO ANO MES DIA_SEMANA HORA TURNO
                             FAIXA_HORARIA                              ~170k
  top_infracao         ANO DESCRICAO_ABRVIADA ENQUADRAMENTO NATUREZA_INFRA
  top_br               ANO NUM_BR_INFRACAO BR_FORMATADA
  top_uf               ANO UF_INFRACAO
  top_municipio        ANO CHAVE_LOCALIDADE UF_INFRACAO NOM_MUNICIPIO
  origem_ocorrencia    ANO UF_PLACA UF_INFRACAO                 (sankey/matrix)
  natureza             ANO NATUREZA_INFRA
  veiculo_especie      ANO ESPECIE TIPO_VEICULO
  veiculo_marca        ANO NOME_VEICULO_MARCA
  abordagem            ANO TIP_ABORDAGEM IND_ASSINOU_AUTO SENTIDO_TRAFEGO
                             QTD_INFRACOES
  velocidade_faixa     ANO FAIXA_VELOCIDADE (0-40,41-60,...,120+,NULL)
  km_faixa             ANO NUM_BR_INFRACAO BR_FORMATADA FAIXA_KM
                       (000-049..0950-0999 de 50 em 50, 1000-1499, 1500+, NAO_INFORMADO)

Validacao: soma(qtd) == 92.215.588 em TODOS os agregados.
Uso: .venv/bin/python scripts/06_agregar.py
"""
from __future__ import annotations

import time
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
BASE = RAIZ / "dados_tratados" / "base_analitica"
AGG = RAIZ / "dados_tratados" / "agregados"
TMP_DIR = RAIZ / "dados_tratados" / "_ddb_tmp"
TOTAL = 92_215_588

AGREGADOS: dict[str, str] = {
    "tempo_diario": """
        SELECT DATA_INFRACAO, ANO, UF_INFRACAO, MES, QUARTIL, SEMANA_DO_MES,
               DIA_SEMANA, DIA_SEMANA_NUM, FIM_DE_SEMANA,
               count(*) AS qtd
        FROM base GROUP BY ALL""",
    "hora_diaria": """
        SELECT DATA_INFRACAO, ANO, UF_INFRACAO, MES, DIA_SEMANA,
               hour(HORA) AS HORA, TURNO, FAIXA_HORARIA,
               count(*) AS qtd
        FROM base GROUP BY ALL""",
    "top_infracao": """
        SELECT ANO, UF_INFRACAO, DESCRICAO_ABRVIADA, ENQUADRAMENTO, NATUREZA_INFRA,
               count(*) AS qtd
        FROM base GROUP BY ALL""",
    "top_br": """
        SELECT ANO, UF_INFRACAO, NUM_BR_INFRACAO, BR_FORMATADA, count(*) AS qtd
        FROM base GROUP BY ALL""",
    "top_uf": """
        SELECT ANO, UF_INFRACAO, count(*) AS qtd
        FROM base GROUP BY ALL""",
    "top_municipio": """
        SELECT ANO, CHAVE_LOCALIDADE, UF_INFRACAO, NOM_MUNICIPIO,
               count(*) AS qtd
        FROM base GROUP BY ALL""",
    "origem_ocorrencia": """
        SELECT ANO, UF_PLACA, UF_INFRACAO, count(*) AS qtd
        FROM base GROUP BY ALL""",
    "natureza": """
        SELECT ANO, UF_INFRACAO, NATUREZA_INFRA, count(*) AS qtd
        FROM base GROUP BY ALL""",
    "veiculo_especie": """
        SELECT ANO, UF_INFRACAO, ESPECIE, TIPO_VEICULO, count(*) AS qtd
        FROM base GROUP BY ALL""",
    "veiculo_marca": """
        SELECT ANO, UF_INFRACAO, NOME_VEICULO_MARCA, count(*) AS qtd
        FROM base GROUP BY ALL""",
    "abordagem": """
        SELECT ANO, UF_INFRACAO, TIP_ABORDAGEM, IND_ASSINOU_AUTO, SENTIDO_TRAFEGO,
               QTD_INFRACOES, count(*) AS qtd
        FROM base GROUP BY ALL""",
    "velocidade_faixa": """
        SELECT ANO, UF_INFRACAO,
               CASE
                 WHEN try_cast(replace(MED_REALIZADA, ',', '.') AS DOUBLE) IS NULL THEN 'NAO_INFORMADO'
                 WHEN try_cast(replace(MED_REALIZADA, ',', '.') AS DOUBLE) <= 40 THEN '00-40'
                 WHEN try_cast(replace(MED_REALIZADA, ',', '.') AS DOUBLE) <= 60 THEN '41-60'
                 WHEN try_cast(replace(MED_REALIZADA, ',', '.') AS DOUBLE) <= 80 THEN '61-80'
                 WHEN try_cast(replace(MED_REALIZADA, ',', '.') AS DOUBLE) <= 100 THEN '81-100'
                 WHEN try_cast(replace(MED_REALIZADA, ',', '.') AS DOUBLE) <= 120 THEN '101-120'
                 ELSE '120+' END AS FAIXA_VELOCIDADE,
               count(*) AS qtd
        FROM base GROUP BY ALL""",
    "km_faixa": """
        SELECT ANO, UF_INFRACAO, NUM_BR_INFRACAO, BR_FORMATADA,
               CASE
                 WHEN NUM_KM_INFRACAO IS NULL THEN 'NAO_INFORMADO'
                 WHEN NUM_KM_INFRACAO >= 1500 THEN '1500+'
                 WHEN NUM_KM_INFRACAO >= 1000 THEN '1000-1499'
                 ELSE lpad(CAST(CAST(floor(NUM_KM_INFRACAO / 50) * 50 AS INTEGER) AS VARCHAR), 3, '0')
                      || '-' ||
                      lpad(CAST(CAST(floor(NUM_KM_INFRACAO / 50) * 50 + 49 AS INTEGER) AS VARCHAR), 3, '0')
               END AS FAIXA_KM,
               count(*) AS qtd
        FROM base GROUP BY ALL""",
}


def main() -> None:
    AGG.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(":memory:")
    con.execute("SET threads=4")
    con.execute("SET memory_limit='4GB'")
    con.execute("SET preserve_insertion_order=false")

    t0 = time.time()
    glob = str(BASE / "*.parquet")
    # Sem CREATE TEMP TABLE: o spill do materialize de 92M x 37 col estourou
    # o disco livre (8.8 GB). Cada agregado varre os parquets direto — todos os
    # GROUP BY sao de baixa cardinalidade (hash minusculo, sem spill).
    leitura = f"read_parquet('{glob}')"
    print(f"varrendo {glob} diretamente (sem temp table)", flush=True)

    for nome, sql in AGREGADOS.items():
        ta = time.time()
        sql = sql.replace("FROM base", f"FROM {leitura}")
        destino = AGG / f"{nome}.parquet"
        destino.unlink(missing_ok=True)
        con.execute(
            f"COPY ({sql}) TO '{destino}' (FORMAT PARQUET, COMPRESSION 'ZSTD')"
        )
        linhas, soma = con.execute(
            f"SELECT count(*), sum(qtd) FROM read_parquet('{destino}')"
        ).fetchone()
        if soma != TOTAL:
            raise AssertionError(f"{nome}: soma(qtd)={soma} != {TOTAL}")
        print(f"{nome}: {linhas:,} linhas, soma={soma:,} OK "
              f"({destino.stat().st_size // 1024} KB, {time.time()-ta:.0f}s)", flush=True)

    print(f"AGREGADOS_OK {len(AGREGADOS)} arquivos, {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
