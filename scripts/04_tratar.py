#!/usr/bin/env python3
"""
04_tratar.py — Fase 2: tratamento e padronizacao -> BASE ANALITICA (Parquet).

Le os 19 CSV normalizados (dados_brutos/infracoes_*.csv.gz) e gera:
  dados_tratados/base_analitica/infracoes_YYYY.parquet   (28 colunas, ZSTD)
  dados_tratados/resumo_colunas.md                       (estatisticas + resumo)

Padronizacao (todas as colunas de texto):
  sentinela ('-1, -1, NA, N/A, N/I, N-I, N-A, NULL, NULO...) -> NULL
  senao: TRIM -> UPPER -> acentos -> ASCII -> '' -> NULL
Tipos:
  DATA_*        DATE  (ISO 'AAAA-MM-DD' ou 'DD/MM/AAAA' defensivo; invalido -> NULL)
  HORA          TIME  (invalido -> NULL)
  NUM_KM        DOUBLE (virgula ou ponto aceito; negativo -> NULL)
  QTD_INFRACOES BIGINT (<= 0 -> NULL)
  NUM_BR        BIGINT (nao numerico -> NULL)
  COD_INFRACAO  VARCHAR (e' codigo, nao quantidade)
  UF_*          VARCHAR (apenas 27 UFs validas; resto -> NULL)
Derivadas (a partir de DATA_INFRACAO):
  MES     VARCHAR nome do mes (JANEIRO..DEZEMBRO; acento->ASCII: MARCO)
  ANO     SMALLINT (ano da infracao)
  QUARTIL Q1=jan-mar | Q2=abr-jun | Q3=jul-set | Q4=out-dez
Linhas: NENHUMA removida (92.215.588 entram e saem).

Uso: .venv/bin/python scripts/04_tratar.py [ANO ...] [--resumo]
"""
from __future__ import annotations

import json
import sys
import time
import unicodedata
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
BRUTOS = RAIZ / "dados_brutos"
TRATADOS = RAIZ / "dados_tratados"
BASE_DIR = TRATADOS / "base_analitica"
TMP_DIR = TRATADOS / "_ddb_tmp"
VALIDACAO = TRATADOS / "_validacao.jsonl"

TOTAL_ESPERADO = 92_215_588

# ---------------------------------------------------------------------------
# mapeamento de acentos (construido com unicodedata para garantir paridade)
# ---------------------------------------------------------------------------
_par: dict[str, str] = {}
for _ch in "ÁÀÂÃÄÅÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑáàâãäåéèêëíìîïóòôõöúùûüçñ":
    _base = unicodedata.normalize("NFD", _ch)[0]
    _par[_ch] = _base
ACC_SRC = "".join(_par.keys())
ACC_DST = "".join(_par.values())

SENTINELAS = ("-1", "'-1", "NA", "N/A", "N/I", "N-I", "N-A", "NULL", "NULO", "#N/A")
SENT_SQL = ", ".join("'" + s.replace("'", "''") + "'" for s in SENTINELAS)

UFS = (
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO"
).split()
UFS_SQL = ", ".join("'" + u + "'" for u in UFS)

UFS_NAO_NUM = f"({UFS_SQL})"


def p(col: str) -> str:
    """Padroniza texto: sentinela -> NULL; senao TRIM+UPPER+dobrar acentos; '' -> NULL."""
    v = f"upper(trim({col}))"
    return (
        f"CASE WHEN {col} IS NULL OR {v} IN ({SENT_SQL}) THEN NULL "
        f"ELSE NULLIF(translate({v}, '{ACC_SRC}', '{ACC_DST}'), '') END"
    )


def ufs(col: str) -> str:
    """UF: apenas siglas validas (27 UFs); sentinela/lixo -> NULL."""
    v = f"upper(trim({col}))"
    return f"CASE WHEN {v} IN {UFS_NAO_NUM} THEN {v} END"


def dt(col: str) -> str:
    """Data: ISO ou DD/MM/AAAA defensivo; invalida -> NULL."""
    return (
        f"CASE WHEN {col} IS NULL THEN NULL "
        f"WHEN trim({col}) ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$' "
        f"THEN try_cast(trim({col}) AS DATE) "
        f"WHEN trim({col}) ~ '^[0-9]{{2}}/[0-9]{{2}}/[0-9]{{4}}$' "
        f"THEN try_strptime(trim({col}), '%d/%m/%Y')::DATE "
        f"ELSE NULL END"
    )


HORA = "try_cast(trim(hora) AS TIME)"
KM = "try_cast(nullif(replace(trim(num_km_infracao), ',', '.'), '') AS DOUBLE)"
KM_OK = f"CASE WHEN {KM} IS NULL OR {KM} < 0 THEN NULL ELSE {KM} END"
QTD = "try_cast(trim(qtd_infracoes) AS BIGINT)"
QTD_OK = f"CASE WHEN {QTD} IS NULL OR {QTD} <= 0 THEN NULL ELSE {QTD} END"
BR = "try_cast(trim(num_br_infracao) AS BIGINT)"

COLS_SELECT = f"""
    {p('numero_auto')}                          AS NUMERO_AUTO,
    {dt('data_infracao')}                       AS DATA_INFRACAO,
    {HORA}                                      AS HORA,
    {p('tip_abordagem')}                        AS TIP_ABORDAGEM,
    {p('ind_assinou_auto')}                     AS IND_ASSINOU_AUTO,
    {p('ind_veiculo_estrangeiro')}              AS IND_VEICULO_ESTRANGEIRO,
    {p('sentido_trafego')}                      AS SENTIDO_TRAFEGO,
    {ufs('uf_placa')}                           AS UF_PLACA,
    {ufs('uf_infracao')}                        AS UF_INFRACAO,
    {BR}                                        AS NUM_BR_INFRACAO,
    {KM_OK}                                     AS NUM_KM_INFRACAO,
    {p('nom_municipio')}                        AS NOM_MUNICIPIO,
    {p('cod_infracao')}                         AS COD_INFRACAO,
    {p('descricao_abreviada')}                  AS DESCRICAO_ABRVIADA,
    {p('enquadramento')}                        AS ENQUADRAMENTO,
    {dt('data_inicio_vigencia')}                AS DATA_INICIO_VIGENCIA,
    {dt('data_fim_vigencia')}                   AS DATA_FIM_VIGENCIA,
    {p('med_realizada')}                        AS MED_REALIZADA,
    {p('med_considerada')}                      AS MED_CONSIDERADA,
    {p('exc_verificado')}                       AS EXC_VERIFICADO,
    {p('especie')}                              AS ESPECIE,
    {p('nome_veiculo_marca')}                   AS NOME_VEICULO_MARCA,
    {p('nom_modelo_veiculo')}                   AS NOM_MODELO_VEICULO,
    {p('tipo_veiculo')}                         AS TIPO_VEICULO,
    {QTD_OK}                                    AS QTD_INFRACOES
"""

SQL_TRATAR = f"""
SELECT
    {COLS_SELECT},
    CASE MES_NUM
        WHEN 1  THEN 'JANEIRO'
        WHEN 2  THEN 'FEVEREIRO'
        WHEN 3  THEN 'MARCO'
        WHEN 4  THEN 'ABRIL'
        WHEN 5  THEN 'MAIO'
        WHEN 6  THEN 'JUNHO'
        WHEN 7  THEN 'JULHO'
        WHEN 8  THEN 'AGOSTO'
        WHEN 9  THEN 'SETEMBRO'
        WHEN 10 THEN 'OUTUBRO'
        WHEN 11 THEN 'NOVEMBRO'
        WHEN 12 THEN 'DEZEMBRO'
    END AS MES,
    ANO,
    CASE
        WHEN MES_NUM IS NULL THEN NULL
        WHEN MES_NUM <= 3  THEN 'Q1'
        WHEN MES_NUM <= 6  THEN 'Q2'
        WHEN MES_NUM <= 9  THEN 'Q3'
        ELSE 'Q4'
    END AS QUARTIL
FROM (
    SELECT
        *,
        EXTRACT(MONTH FROM {dt('data_infracao')})::SMALLINT AS MES_NUM,
        EXTRACT(YEAR  FROM {dt('data_infracao')})::SMALLINT AS ANO
    FROM stage
)
"""

SQL_VALIDACAO = f"""
SELECT
    count(*)                                                          AS linhas,
    count(*) FILTER (WHERE data_infracao IS NOT NULL AND _d  IS NULL) AS data_ruim,
    count(*) FILTER (WHERE data_infracao IS NOT NULL AND _d  IS NOT NULL
                      AND EXTRACT(YEAR FROM _d)::INT <> {{ANO}})       AS ano_divergente,
    count(*) FILTER (WHERE hora IS NOT NULL AND _h IS NULL)           AS hora_ruima,
    count(*) FILTER (WHERE uf_placa IS NOT NULL AND _ufp IS NULL)     AS uf_placa_invalida,
    count(*) FILTER (WHERE uf_infracao IS NOT NULL AND _ufi IS NULL)  AS uf_infracao_invalida,
    count(*) FILTER (WHERE num_km_infracao IS NOT NULL AND _km IS NULL) AS km_invalido,
    count(*) FILTER (WHERE qtd_infracoes IS NOT NULL AND _q IS NULL)  AS qtd_invalida,
    count(*) FILTER (WHERE num_br_infracao IS NOT NULL AND _br IS NULL) AS br_invalido,
    count(*) FILTER (WHERE upper(trim(especie)) IN ({SENT_SQL})) AS especie_sentinela
FROM (
    SELECT
        data_infracao, hora, uf_placa, uf_infracao,
        num_km_infracao, qtd_infracoes, num_br_infracao, especie,
        {dt('data_infracao')} AS _d,
        {HORA}                AS _h,
        {ufs('uf_placa')}     AS _ufp,
        {ufs('uf_infracao')}  AS _ufi,
        {KM_OK}               AS _km,
        {QTD_OK}              AS _q,
        {BR}                  AS _br
    FROM stage
)
"""


def criar_stage(con: duckdb.DuckDBPyConnection, arquivo: Path, paralelo: bool = True) -> None:
    """Materializa o CSV (1x decompress) em TEMP; metricas e COPY leem daqui."""
    q = chr(34)  # aspas duplas dentro do SQL: quote='"'
    opts = (
        "header=true, delim=';', all_varchar=true, strict_mode=false, "
        + "quote='" + q + "', escape='" + q + "', "
        + "parallel=" + ("true" if paralelo else "false")
    )
    con.execute("DROP TABLE IF EXISTS stage")
    con.execute(
        f"CREATE TEMP TABLE stage AS "
        f"SELECT * FROM read_csv('{arquivo}', {opts})"
    )


def tratar_ano(con: duckdb.DuckDBPyConnection, ano: int) -> dict:
    arquivo = BRUTOS / f"infracoes_{ano}.csv.gz"
    if not arquivo.exists():
        raise FileNotFoundError(
            f"{arquivo} nao encontrado (remonte as partes: cat {arquivo.name}.* > {arquivo.name})"
        )
    destino = BASE_DIR / f"infracoes_{ano}.parquet"
    destino.unlink(missing_ok=True)

    try:
        criar_stage(con, arquivo, paralelo=True)
        metricas = con.execute(SQL_VALIDACAO.replace('{ANO}', str(ano))).fetchone()
        con.execute(
            f"COPY ({SQL_TRATAR}) TO '{destino}' "
            f"(FORMAT PARQUET, COMPRESSION 'ZSTD')"
        )
    except duckdb.NotImplementedException:
        print(f"  [{ano}] reader paralelo recusou o arquivo; retry serial", flush=True)
        criar_stage(con, arquivo, paralelo=False)
        destino.unlink(missing_ok=True)
        metricas = con.execute(SQL_VALIDACAO.replace('{ANO}', str(ano))).fetchone()
        con.execute(
            f"COPY ({SQL_TRATAR}) TO '{destino}' "
            f"(FORMAT PARQUET, COMPRESSION 'ZSTD')"
        )

    con.execute("DROP TABLE IF EXISTS stage")
    linhas = con.execute(f"SELECT count(*) FROM read_parquet('{destino}')").fetchone()[0]
    if linhas != metricas[0]:
        raise AssertionError(f"[{ano}] contagem divergente: fonte={metricas[0]} parquet={linhas}")

    nomes = [
        "linhas", "data_ruim", "ano_divergente", "hora_ruima",
        "uf_placa_invalida", "uf_infracao_invalida", "km_invalido",
        "qtd_invalida", "br_invalido", "especie_sentinela",
    ]
    m = dict(zip(nomes, metricas))
    m["ano"] = ano
    m["parquet_mb"] = round(destino.stat().st_size / 1e6, 1)
    return m


# ---------------------------------------------------------------------------
# fase B — resumo das colunas
# ---------------------------------------------------------------------------
def fase_b(con: duckdb.DuckDBPyConnection, validacoes: list[dict]) -> Path:
    glob = str(BASE_DIR / "*.parquet")
    con.execute(f"CREATE OR REPLACE VIEW base AS SELECT * FROM read_parquet('{glob}')")
    total = con.execute("SELECT count(*) FROM base").fetchone()[0]
    if total != TOTAL_ESPERADO:
        raise AssertionError(f"TOTAL global {total:,} != esperado {TOTAL_ESPERADO:,}")

    cols = [
        r[0] for r in con.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='base' ORDER BY ordinal_position"
        ).fetchall()
    ]
    tipos = dict(con.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name='base'"
    ).fetchall())

    aggs = ["count(*) AS n"]
    for c in cols:
        aggs.append(f"count(*) FILTER (WHERE \"{c}\" IS NULL) AS \"nul_{c}\"")
        aggs.append(f"approx_count_distinct(\"{c}\") AS \"d_{c}\"")
    row = dict(zip(
        ["n"] + [x for c in cols for x in (f"nul_{c}", f"d_{c}")],
        con.execute(f"SELECT {', '.join(aggs)} FROM base").fetchone(),
    ))

    # nulos por era (era1 2007-18 | era2 2019-21 | era3 2022-25)
    eras = {"era1": "ANO BETWEEN 2007 AND 2018", "era2": "ANO BETWEEN 2019 AND 2021",
            "era3": "ANO >= 2022"}
    aggs_e = []
    for c in cols:
        for e, w in eras.items():
            aggs_e.append(
                f"round(100.0 * count(*) FILTER (WHERE \"{c}\" IS NULL AND {w}) "
                f"/ nullif(count(*) FILTER (WHERE {w}), 0), 1) AS \"{e}__{c}\""
            )
    row_e = dict(zip(
        [f"{e}__{c}" for c in cols for e in eras],
        con.execute(f"SELECT {', '.join(aggs_e)} FROM base").fetchone(),
    ))

    # redundancias / resumos possiveis
    red = con.execute("""
        SELECT
            approx_count_distinct(COD_INFRACAO) AS n_cod,
            approx_count_distinct(COD_INFRACAO || '|' || coalesce(ENQUADRAMENTO,'')) AS n_cod_enq,
            approx_count_distinct(COD_INFRACAO || '|' || coalesce(DESCRICAO_ABRVIADA,'')) AS n_cod_desc,
            approx_count_distinct(ENQUADRAMENTO || '|' || coalesce(DESCRICAO_ABRVIADA,'')) AS n_enq_desc,
            approx_count_distinct(NOME_VEICULO_MARCA) AS n_marca,
            approx_count_distinct(NOM_MODELO_VEICULO) AS n_modelo,
            approx_count_distinct(NOM_MUNICIPIO) AS n_municipio,
            count(*) FILTER (WHERE MED_REALIZADA IS NOT NULL
                 AND try_cast(replace(MED_REALIZADA,',','.') AS DOUBLE) IS NULL) AS med_ruim,
            count(*) FILTER (WHERE MED_REALIZADA IS NOT NULL) AS med_nao_nulo,
            count(*) FILTER (WHERE MED_CONSIDERADA IS NOT NULL
                 AND try_cast(replace(MED_CONSIDERADA,',','.') AS DOUBLE) IS NULL) AS medc_ruim,
            count(*) FILTER (WHERE MED_CONSIDERADA IS NOT NULL) AS medc_nao_nulo
        FROM base
    """).fetchone()
    red = dict(zip(
        ["n_cod", "n_cod_enq", "n_cod_desc", "n_enq_desc", "n_marca", "n_modelo",
         "n_municipio", "med_ruim", "med_nao_nulo", "medc_ruim", "medc_nao_nulo"], red))

    # amostras de MED_*
    amostras = con.execute("""
        SELECT MED_REALIZADA, count(*) FROM base
        WHERE MED_REALIZADA IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 6
    """).fetchall()

    # ------------------------------------------------------------------ md
    def pct(c: str) -> str:
        return f"{100.0 * row[f'nul_{c}'] / row['n']:.2f}%"

    linhas_md = [
        "# resumo_colunas — base analítica (dados_tratados)",
        "",
        f"- **Linhas:** {row['n']:,} · **Colunas:** {len(cols)} · "
        f"Gerado por `scripts/04_tratar.py` em {time.strftime('%Y-%m-%d %H:%M')}.",
        "- **Fonte:** `dados_brutos/infracoes_2007..2025.csv.gz` (19 arquivos, schema canônico 25 col).",
        "- Colunas de texto: sentinela → `NULL`; `TRIM` + `MAIÚSCULAS` + acentos→ASCII. "
        "Colunas derivadas: `MES` (nome do mês: JANEIRO…DEZEMBRO), `ANO`, `QUARTIL` (Q1=jan-mar, Q2=abr-jun, Q3=jul-set, Q4=out-dez).",
        "",
        "## 1. Estatísticas globais",
        "",
        "| # | Coluna | Tipo | Nulos | Nulos % | Distintos (aprox) |",
        "|---|--------|------|------:|--------:|------------------:|",
    ]
    for i, c in enumerate(cols, 1):
        linhas_md.append(
            f"| {i} | `{c}` | {tipos[c]} | {row[f'nul_{c}']:,} | {pct(c)} | {row[f'd_{c}']:,} |"
        )

    linhas_md += [
        "",
        "## 2. Nulos por era (era1 2007–2018 · era2 2019–2021 · era3 2022–2025)",
        "",
        "| Coluna | era1 | era2 | era3 |",
        "|--------|-----:|-----:|-----:|",
    ]
    for c in cols:
        v = [row_e[f"{e}__{c}"] for e in eras]
        linhas_md.append(f"| `{c}` | {v[0]}% | {v[1]}% | {v[2]}% |")

    linhas_md += ["", "## 3. Anomalias corrigidas na padronização", "",
                  "| Ano | Linhas | Datas inválidas | Ano divergente | Hora inválida | UF placa inv. | UF infra inv. | KM inv. | Qtd inv. | BR inv. | Espécie sentinela | Parquet MB |",
                  "|----:|-------:|----------------:|---------------:|--------------:|--------------:|--------------:|--------:|---------:|--------:|------------------:|-----------:|"]
    for m in validacoes:
        linhas_md.append(
            f"| {m['ano']} | {m['linhas']:,} | {m['data_ruim']} | {m['ano_divergente']} | "
            f"{m['hora_ruima']} | {m['uf_placa_invalida']} | {m['uf_infracao_invalida']} | "
            f"{m['km_invalido']} | {m['qtd_invalida']} | {m['br_invalido']} | "
            f"{m['especie_sentinela']} | {m['parquet_mb']} |"
        )

    # ---------------------------------------------------------- recomendacoes
    fd_enq = red["n_cod_enq"] <= red["n_cod"] * 1.02
    fd_desc = red["n_cod_desc"] <= red["n_cod"] * 1.02
    med_ok = red["med_nao_nulo"] > 0 and red["med_ruim"] == 0
    medc_ok = red["medc_nao_nulo"] > 0 and red["medc_ruim"] == 0

    linhas_md += [
        "",
        "## 4. Colunas que PODEM ser resumidas",
        "",
        f"- **`DESCRICAO_ABRVIADA` / `ENQUADRAMENTO` vs `COD_INFRACAO`**: "
        f"{red['n_cod']:,} códigos distintos; pares (código,enquadramento) ≈ {red['n_cod_enq']:,}; "
        f"pares (código,descrição) ≈ {red['n_cod_desc']:,}; "
        f"(enquadramento,descrição) ≈ {red['n_enq_desc']:,}. "
        + ("Os textos são **funcionalmente dependentes do código** → em bases "
           "modeláveis podem ser **resumidos em `COD_INFRACAO`** (dicionário à parte), "
           "eliminando redundância." if fd_enq and fd_desc else
           "Há códigos com múltiplos textos → manter os três na base analítica; "
           "na modelável resumir via dicionário código→texto."),
        f"- **`NOME_VEICULO_MARCA` + `NOM_MODELO_VEICULO`**: ≈ {red['n_marca']:,} marcas e "
        f"≈ {red['n_modelo']:,} modelos (carteira aberta, grafias livres) → **resumir em "
        "`ESPECIE`/`TIPO_VEICULO`** (já padronizados) ou dicionário de marcas controlado "
        "antes de uso como categoria.",
        f"- **`NOM_MUNICIPIO`**: ≈ {red['n_municipio']:,} municípios distintos (texto) → "
        "**resumir em código IBGE** (ou `UF_INFRACAO`+código) para agregação/geolocalização "
        "estável.",
        "- **`HORA`**: detalhe fino já coberto por `MES`/`ANO`/`QUARTIL` → em bases "
        "modeláveis **resumir em turno/faixa horária** (MADRUGADA/MANHÃ/TARDE/NOITE).",
        "- **`NUMERO_AUTO`**: identificador (≈1 por linha) — **não resume**: é a chave do auto "
        "de infração; servir de join/contagem, não de categoria.",
        "",
        "## 5. Colunas que PRECISAM de resumo/atenção",
        "",
        "- **Lacunas de era** (null100% em eras inteiras — ausência legítima na fonte, "
        "não erro): `NUMERO_AUTO` (era1), `HORA` (era1–2 parcial), `TIPO_VEICULO` (era1–2), "
        "`QTD_INFRACOES` (era1–2), `COD_INFRACAO` (2007) — ver matriz §2. "
        "Em cruzamentos entre eras, usar apenas colunas com cobertura nas duas.",
        "- **Sentinelas de origem** (`'-1`, `-1`, `NA`…) convertidas para `NULL` "
        "(§3) — nunca imputar 0/'' nelas: o `NULL` é a marca de \"não informado\".",
        f"- **`MED_REALIZADA`/`MED_CONSIDERADA`**: "
        + (f"100% numéricas após vírgula→ponto (0 inválidas em "
           f"{red['med_nao_nulo']:,}/{red['medc_nao_nulo']:,}) → **podem virar DOUBLE** "
           "numa próxima etapa sem perda." if med_ok and medc_ok else
           "ainda com valores não numéricos misturados → **precisam de resumo/conversão** "
           "controlada (mapear unidades) antes de virar DOUBLE."),
        f"- **`UF_PLACA`/`UF_INFRACAO`**: apenas 27 UFs aceitas; inválidas viram `NULL` "
        f"({sum(m['uf_placa_invalida'] + m['uf_infracao_invalida'] for m in validacoes):,} "
        "células corrigidas no total).",
        "",
        "---",
        "Leitura: `read_parquet('dados_tratados/base_analitica/*.parquet')` (DuckDB/pandas).",
    ]

    out = TRATADOS / "resumo_colunas.md"
    out.write_text("\n".join(linhas_md) + "\n", encoding="utf-8")
    print(f"resumo -> {out}", flush=True)
    return out


def main() -> None:
    argv = sys.argv[1:]
    so_resumo = "--resumo" in argv
    anos = [int(a) for a in argv if a.isdigit()] or ([] if so_resumo else list(range(2007, 2026)))
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    if len(anos) == 19:
        VALIDACAO.unlink(missing_ok=True)  # recomeco completo

    con = duckdb.connect()
    con.execute("SET threads=2")
    con.execute("SET memory_limit='2400MB'")
    con.execute(f"SET temp_directory='{TMP_DIR}'")
    con.execute("SET preserve_insertion_order=false")

    validacoes: list[dict] = []
    t0 = time.time()
    for ano in anos:
        ta = time.time()
        m = tratar_ano(con, ano)
        validacoes.append(m)
        with VALIDACAO.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(m, ensure_ascii=False) + "\n")
        print(
            f"[{ano}] {m['linhas']:,} linhas -> {m['parquet_mb']} MB "
            f"({time.time() - ta:.0f}s) | uf_placa_inv={m['uf_placa_invalida']} "
            f"uf_infra_inv={m['uf_infracao_invalida']} especie_sent={m['especie_sentinela']} "
            f"data_ruim={m['data_ruim']} ano_div={m['ano_divergente']}",
            flush=True,
        )

    if so_resumo or len(anos) == 19:
        if so_resumo:
            validacoes = [
                json.loads(l)
                for l in VALIDACAO.read_text(encoding="utf-8").splitlines()
                if l.strip()
            ]
        # fase B so faz sentido com a base completa (19 no jsonl)
        fase_b(con, validacoes)
    else:
        print("parcial: pulando fase B (rode com --resumo apos os 19)", flush=True)

    if so_resumo:
        print("resumo ok", flush=True)
        return
    total = sum(m["linhas"] for m in validacoes)
    print(f"OK {len(anos)} anos, {total:,} linhas, {time.time() - t0:.0f}s", flush=True)
    if len(anos) == 19 and total != TOTAL_ESPERADO:
        raise SystemExit(f"TOTAL {total} != {TOTAL_ESPERADO}")


if __name__ == "__main__":
    main()
