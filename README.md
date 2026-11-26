# PRF-MULTAS-PROJETO

Pipeline de **engenharia de dados** com as **multas de trânsito da PRF (2007–2025)**:
ingestão de fontes brutas → normalização → **base analítica padronizada**.

| Métrica | Valor |
|---------|-------|
| Registros | **92.215.588** (19 anos) |
| Esquema | base analítica **37 col** (25 canônicas + 12 derivadas) · 13 agregados |
| Motor | DuckDB (100% Python: `import duckdb`) |
| Base tratada | 19 Parquets ZSTD · **1,4 GB** em `dados_tratados/` |

## Status

| Fase | Descrição | PR |
|------|-----------|----|
| ✅ 1 | Ingestão + normalização (schema canônico 25 col) | [#1](https://github.com/Matheus-Trajano/PRF-MULTAS-PROJETO/pull/1) |
| ✅ — | `dados_brutos/` publicado no GitHub (gzip em volumes ≤ 95 MB + `SHA256SUMS.txt`) | [#2](https://github.com/Matheus-Trajano/PRF-MULTAS-PROJETO/pull/2) |
| ✅ 2 | Tratamento → **base analítica** (padronização, 28 colunas, relatórios) | [#3](https://github.com/Matheus-Trajano/PRF-MULTAS-PROJETO/pull/3) |
| ✅ 3 | Análise, enriquecimento (37 col), 12 agregados, docs C/D e dashboard Plotly | [#4](https://github.com/Matheus-Trajano/PRF-MULTAS-PROJETO/pull/4) |
| ✅ 3 | KM em faixas (13º agregado) + dashboard **Dash** com drill por clique | [#5](https://github.com/Matheus-Trajano/PRF-MULTAS-PROJETO/pull/5) |
| ✅ 6 | Parte 6 — gráficos no padrão da referência: top10 multas → `resultados/` | [#6](https://github.com/Matheus-Trajano/PRF-MULTAS-PROJETO/pull/6) |
| ✅ 6 | Parte 6 — **g2**: drill interativo ano→mês→semana→dia, % do período pai | [#7](https://github.com/Matheus-Trajano/PRF-MULTAS-PROJETO/pull/7) |
| ✅ 6 | Parte 6 — **g3**: top10 tipos de veículo × causas por período (menus em cascata) | [#8](https://github.com/Matheus-Trajano/PRF-MULTAS-PROJETO/pull/8) |

## Estrutura

```
.
├── scripts/                  # pipeline (ordem numérica)
│   ├── extract_rar.js        # extração dos RARs (node)
│   ├── 01_unificar_anos.py   # 2007–2017: unifica por ano
│   ├── 01b_montar_partes.py  # (histórico, superseded)
│   ├── 02_extrair_unificar.py# 2018–2025: unzip+sanear+unificar
│   ├── 03_normalizar.py      # → 25 col canônicas (TRIM, datas ISO, NULLs)
│   ├── 04_tratar.py          # → base analítica 28 col (Parquet)
│   ├── 05_enriquecer.py      # → 37 col (+9 derivadas, Etapa A)
│   └── 06_agregar.py         # → 13 agregados p/ gráficos (Etapa B)
├── notebooks/
│   ├── 00_pipeline_completo.ipynb  # TODOS os scripts + validações executáveis
│   ├── 05_eda_plotly.ipynb         # dashboard Plotly: filtros + cascata (Etapa E)
│   ├── 09_parte6_graficos.ipynb    # Parte 6: gráficos Plotly (padrão da referência)
│   └── _build_graficos.py          # builder que gera/executa o notebook 09
├── apps/
│   └── dashboard.py                # dashboard Dash E2: drill por clique (4 abas)
├── resultados/                # gráficos exportados (HTML autocontido — versionado)
│   ├── g1_top10_multas.html   # g1: top10 causas 2007–2025
│   ├── g2_drill_temporal.html # g2: drill ano→mês→semana→dia (% do período pai)
│   └── g3_top10_veiculos.html # g3: top10 tipos × causas por período (menus)
├── docs/                      # análise de variáveis, catálogo e interações
├── dados_brutos/             # fonte: 19 .csv.gz + partes + checksums + README
├── dados_tratados/           # base analítica (Parquet) + relatórios (versionados)
│   ├── base_analitica/       # infracoes_YYYY.parquet (19) — fora do Git
│   ├── agregados/            # 13 agregados p/ gráficos — fora do Git
│   ├── resumo_colunas.md     # stats, nulos por era, colunas a resumir
│   └── valores_rejeitados.md # o que virou NULL (valor a valor)
├── logs/ingestao_multas.md   # log completo de execuções
└── requirements.txt          # duckdb, pandas, plotly, dash, nbclient…
```

## Como executar

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# Fase 1 (do zero: requer fontes do Drive — ver dados_brutos/README.md)
node scripts/extract_rar.js <rar> <outDir>          # 2007–2017
.venv/bin/python scripts/01_unificar_anos.py        # …
.venv/bin/python scripts/02_extrair_unificar.py 2018 … 2025
gzip -6 dados_brutos/infracoes_*.csv
.venv/bin/python scripts/03_normalizar.py

# Fase 2 (usa os .csv.gz já normalizados; ~1 h)
.venv/bin/python scripts/04_tratar.py               # 19 anos + resumo
.venv/bin/python scripts/04_tratar.py --resumo      # só regenera relatórios

# Fase 3 (enriquecimento + agregados; minutos)
.venv/bin/python scripts/05_enriquecer.py           # → 37 col (Etapa A)
.venv/bin/python scripts/06_agregar.py             # → 13 agregados (Etapa B)

# Dashboard Dash (E2 — drill por clique; http://0.0.0.0:8050)
.venv/bin/python apps/dashboard.py

# Parte 6 — gráficos (gera 09_parte6_graficos.ipynb + resultados/*.html)
.venv/bin/python notebooks/_build_graficos.py

# Notebooks (validações em segundos; recria os scripts via %%writefile)
.venv/bin/pip install notebook        # ou abrir no VS Code / Colab
.venv/bin/jupyter notebook notebooks/00_pipeline_completo.ipynb
.venv/bin/jupyter notebook notebooks/05_eda_plotly.ipynb   # EDA interativa (Etapa E)
.venv/bin/jupyter notebook notebooks/09_parte6_graficos.ipynb
```

## Dados

- **`dados_brutos/`** — 19 CSVs normalizados; como o Git limita arquivos a 100 MB,
  os maiores estão em volumes `.aa/.ab` (remontagem + checksums em
  [`dados_brutos/README.md`](dados_brutos/README.md); âncora: Release
  [`dados-brutos`](https://github.com/Matheus-Trajano/PRF-MULTAS-PROJETO/releases/tag/dados-brutos)).
- **`dados_tratados/`** — base analítica:
  ```sql
  SELECT * FROM read_parquet('dados_tratados/base_analitica/*.parquet');
  ```
  Relatórios: [`resumo_colunas.md`](dados_tratados/resumo_colunas.md) ·
  [`valores_rejeitados.md`](dados_tratados/valores_rejeitados.md) ·
  [`dados_tratados/README.md`](dados_tratados/README.md).

## Gráficos (`resultados/`)

Padrão do repositório de referência
[`PRF_pandas_plotly-2023-2025`](https://github.com/Matheus-Trajano/PRF_pandas_plotly-2023-2025):
cada gráfico vive no notebook da sua etapa (`notebooks/09_parte6_graficos.ipynb`),
responde a uma pergunta (células **Pergunta/Resposta** com os números), tem
**título com a mensagem principal** + legenda de 2 linhas, `assert`s antes de
salvar e é exportado **autocontido** (`include_plotlyjs=True`, abre offline) por
`salvar_grafico()`.

| # | Gráfico | Arquivo |
|---|---------|---------|
| 1 | Top 10 causas que mais ocorrem — todos os anos (2007–2025); velocidade = 52% | `resultados/g1_top10_multas.html` |
| 2 | Drill interativo ano→mês→semana→dia; **% do período pai** (cada nível soma 100%) | `resultados/g2_drill_temporal.html` |
| 3 | Top10 tipos de veículo (eixo híbrido TIPO+ESPÉCIE); clique no tipo → top5 causas do período | `resultados/g3_top10_veiculos.html` |

## Regras de dados (decisões de negócio)

- **jun/2024 não existe** na base (11 meses em 2024) — tratada como inexistente
  (`MESES_INEXISTENTES`), nunca como pendência.
- Colunas de texto: sentinela (`'-1`, `-1`, `NA`…) → `NULL`; `TRIM` + MAIÚSCULAS +
  acentos→ASCII. UF só com as 27 siglas válidas.
- **`QUARTIL`** = 4 períodos de 3 meses (Q1 jan-mar … Q4 out-dez).
- **`MES`** = nome do mês (JANEIRO…DEZEMBRO).
- Nenhuma linha é removida no tratamento (92.215.588 entram e saem).

## Referências

- Estrutura/analítica espelha o projeto de referência FAP-2026 (bases
  analítica + modelável; dicionário; asserts).
- Notebooks por etapa, gráficos Plotly e pasta `resultados/` espelham
  [`PRF_pandas_plotly-2023-2025`](https://github.com/Matheus-Trajano/PRF_pandas_plotly-2023-2025).
- Log de execuções: [`logs/ingestao_multas.md`](logs/ingestao_multas.md).
