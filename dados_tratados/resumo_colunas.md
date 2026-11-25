# resumo_colunas — base analítica (dados_tratados)

- **Linhas:** 92,215,588 · **Colunas:** 28 · Gerado por `scripts/04_tratar.py` em 2026-11-25 19:16.
- **Fonte:** `dados_brutos/infracoes_2007..2025.csv.gz` (19 arquivos, schema canônico 25 col).
- Colunas de texto: sentinela → `NULL`; `TRIM` + `MAIÚSCULAS` + acentos→ASCII. Colunas derivadas: `MES` (nome do mês: JANEIRO…DEZEMBRO), `ANO`, `QUARTIL` (Q1=jan-mar, Q2=abr-jun, Q3=jul-set, Q4=out-dez).

## 1. Estatísticas globais

| # | Coluna | Tipo | Nulos | Nulos % | Distintos (aprox) |
|---|--------|------|------:|--------:|------------------:|
| 1 | `NUMERO_AUTO` | VARCHAR | 47,053,140 | 51.03% | 46,181,829 |
| 2 | `DATA_INFRACAO` | DATE | 0 | 0.00% | 6,969 |
| 3 | `HORA` | TIME | 22,679,289 | 24.59% | 85,475 |
| 4 | `TIP_ABORDAGEM` | VARCHAR | 0 | 0.00% | 2 |
| 5 | `IND_ASSINOU_AUTO` | VARCHAR | 52,097,346 | 56.50% | 2 |
| 6 | `IND_VEICULO_ESTRANGEIRO` | VARCHAR | 744 | 0.00% | 13 |
| 7 | `SENTIDO_TRAFEGO` | VARCHAR | 21,898,868 | 23.75% | 3 |
| 8 | `UF_PLACA` | VARCHAR | 14,393,024 | 15.61% | 26 |
| 9 | `UF_INFRACAO` | VARCHAR | 0 | 0.00% | 26 |
| 10 | `NUM_BR_INFRACAO` | BIGINT | 3 | 0.00% | 182 |
| 11 | `NUM_KM_INFRACAO` | DOUBLE | 0 | 0.00% | 1,557 |
| 12 | `NOM_MUNICIPIO` | VARCHAR | 4,484 | 0.00% | 3,228 |
| 13 | `COD_INFRACAO` | VARCHAR | 33,673,148 | 36.52% | 410 |
| 14 | `DESCRICAO_ABRVIADA` | VARCHAR | 0 | 0.00% | 705 |
| 15 | `ENQUADRAMENTO` | VARCHAR | 0 | 0.00% | 564 |
| 16 | `DATA_INICIO_VIGENCIA` | DATE | 77,018 | 0.08% | 38 |
| 17 | `DATA_FIM_VIGENCIA` | DATE | 59,769,829 | 64.82% | 19 |
| 18 | `MED_REALIZADA` | VARCHAR | 27,304,163 | 29.61% | 41,410 |
| 19 | `MED_CONSIDERADA` | VARCHAR | 17,662,677 | 19.15% | 88,185 |
| 20 | `EXC_VERIFICADO` | VARCHAR | 18,239,216 | 19.78% | 49,396 |
| 21 | `ESPECIE` | VARCHAR | 17,126,776 | 18.57% | 10 |
| 22 | `NOME_VEICULO_MARCA` | VARCHAR | 29,357,950 | 31.84% | 38,221 |
| 23 | `NOM_MODELO_VEICULO` | VARCHAR | 18,745,077 | 20.33% | 137,629 |
| 24 | `TIPO_VEICULO` | VARCHAR | 63,247,959 | 68.59% | 31 |
| 25 | `QTD_INFRACOES` | BIGINT | 52,795,250 | 57.25% | 2 |
| 26 | `MES` | VARCHAR | 0 | 0.00% | 12 |
| 27 | `ANO` | SMALLINT | 0 | 0.00% | 19 |
| 28 | `QUARTIL` | VARCHAR | 0 | 0.00% | 4 |

## 2. Nulos por era (era1 2007–2018 · era2 2019–2021 · era3 2022–2025)

| Coluna | era1 | era2 | era3 |
|--------|-----:|-----:|-----:|
| `NUMERO_AUTO` | 100.0% | 0.0% | 0.0% |
| `DATA_INFRACAO` | 0.0% | 0.0% | 0.0% |
| `HORA` | 48.2% | 0.0% | 0.0% |
| `TIP_ABORDAGEM` | 0.0% | 0.0% | 0.0% |
| `IND_ASSINOU_AUTO` | 90.1% | 0.0% | 33.4% |
| `IND_VEICULO_ESTRANGEIRO` | 0.0% | 0.0% | 0.0% |
| `SENTIDO_TRAFEGO` | 46.5% | 0.0% | 0.0% |
| `UF_PLACA` | 0.8% | 69.0% | 9.9% |
| `UF_INFRACAO` | 0.0% | 0.0% | 0.0% |
| `NUM_BR_INFRACAO` | 0.0% | 0.0% | 0.0% |
| `NUM_KM_INFRACAO` | 0.0% | 0.0% | 0.0% |
| `NOM_MUNICIPIO` | 0.0% | 0.0% | 0.0% |
| `COD_INFRACAO` | 71.6% | 0.0% | 0.0% |
| `DESCRICAO_ABRVIADA` | 0.0% | 0.0% | 0.0% |
| `ENQUADRAMENTO` | 0.0% | 0.0% | 0.0% |
| `DATA_INICIO_VIGENCIA` | 0.2% | 0.0% | 0.0% |
| `DATA_FIM_VIGENCIA` | 31.0% | 100.0% | 100.0% |
| `MED_REALIZADA` | 37.5% | 0.0% | 33.3% |
| `MED_CONSIDERADA` | 37.5% | 0.0% | 0.0% |
| `EXC_VERIFICADO` | 38.7% | 0.0% | 0.0% |
| `ESPECIE` | 19.8% | 47.1% | 0.7% |
| `NOME_VEICULO_MARCA` | 46.6% | 43.9% | 1.2% |
| `NOM_MODELO_VEICULO` | 5.2% | 100.0% | 0.4% |
| `TIPO_VEICULO` | 100.0% | 100.0% | 0.1% |
| `QTD_INFRACOES` | 100.0% | 35.5% | 0.0% |
| `MES` | 0.0% | 0.0% | 0.0% |
| `ANO` | 0.0% | 0.0% | 0.0% |
| `QUARTIL` | 0.0% | 0.0% | 0.0% |

## 3. Anomalias corrigidas na padronização

| Ano | Linhas | Datas inválidas | Ano divergente | Hora inválida | UF placa inv. | UF infra inv. | KM inv. | Qtd inv. | BR inv. | Espécie sentinela | Parquet MB |
|----:|-------:|----------------:|---------------:|--------------:|--------------:|--------------:|--------:|---------:|--------:|------------------:|-----------:|
| 2007 | 1,855,460 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 17.4 |
| 2008 | 2,432,797 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 25.5 |
| 2009 | 3,045,607 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 32.9 |
| 2010 | 3,038,357 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 32.6 |
| 2011 | 2,884,305 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 31.2 |
| 2012 | 2,843,728 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 31.0 |
| 2013 | 3,251,800 | 0 | 0 | 0 | 1267 | 0 | 0 | 0 | 0 | 0 | 34.5 |
| 2014 | 3,327,193 | 0 | 0 | 0 | 13 | 0 | 0 | 0 | 0 | 0 | 34.9 |
| 2015 | 5,408,986 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 68.5 |
| 2016 | 5,584,915 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 70.8 |
| 2017 | 6,023,833 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 77.5 |
| 2018 | 7,356,159 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 97.3 |
| 2019 | 5,742,110 | 0 | 0 | 0 | 1112328 | 0 | 0 | 0 | 0 | 3027027 | 96.4 |
| 2020 | 5,182,537 | 0 | 0 | 0 | 95164 | 0 | 0 | 0 | 0 | 2389858 | 84.1 |
| 2021 | 5,241,299 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2200340 | 85.6 |
| 2022 | 4,135,523 | 0 | 0 | 0 | 875441 | 0 | 0 | 0 | 0 | 205630 | 88.0 |
| 2023 | 5,946,483 | 0 | 0 | 0 | 1071395 | 0 | 0 | 0 | 0 | 8695 | 125.8 |
| 2024 | 8,710,022 | 0 | 0 | 0 | 762438 | 0 | 0 | 0 | 0 | 0 | 176.4 |
| 2025 | 10,204,474 | 0 | 0 | 0 | 23112 | 0 | 0 | 0 | 0 | 0 | 199.0 |

## 4. Colunas que PODEM ser resumidas

- **`DESCRICAO_ABRVIADA` / `ENQUADRAMENTO` vs `COD_INFRACAO`**: 410 códigos distintos; pares (código,enquadramento) ≈ 789; pares (código,descrição) ≈ 466; (enquadramento,descrição) ≈ 1,102. Há códigos com múltiplos textos → manter os três na base analítica; na modelável resumir via dicionário código→texto.
- **`NOME_VEICULO_MARCA` + `NOM_MODELO_VEICULO`**: ≈ 38,221 marcas e ≈ 137,629 modelos (carteira aberta, grafias livres) → **resumir em `ESPECIE`/`TIPO_VEICULO`** (já padronizados) ou dicionário de marcas controlado antes de uso como categoria.
- **`NOM_MUNICIPIO`**: ≈ 3,228 municípios distintos (texto) → **resumir em código IBGE** (ou `UF_INFRACAO`+código) para agregação/geolocalização estável.
- **`HORA`**: detalhe fino já coberto por `MES`/`ANO`/`QUARTIL` → em bases modeláveis **resumir em turno/faixa horária** (MADRUGADA/MANHÃ/TARDE/NOITE).
- **`NUMERO_AUTO`**: identificador (≈1 por linha) — **não resume**: é a chave do auto de infração; servir de join/contagem, não de categoria.

## 5. Colunas que PRECISAM de resumo/atenção

- **Lacunas de era** (null100% em eras inteiras — ausência legítima na fonte, não erro): `NUMERO_AUTO` (era1), `HORA` (era1–2 parcial), `TIPO_VEICULO` (era1–2), `QTD_INFRACOES` (era1–2), `COD_INFRACAO` (2007) — ver matriz §2. Em cruzamentos entre eras, usar apenas colunas com cobertura nas duas.
- **Sentinelas de origem** (`'-1`, `-1`, `NA`…) convertidas para `NULL` (§3) — nunca imputar 0/'' nelas: o `NULL` é a marca de "não informado".
- **`MED_REALIZADA`/`MED_CONSIDERADA`**: ainda com valores não numéricos misturados → **precisam de resumo/conversão** controlada (mapear unidades) antes de virar DOUBLE.
- **`UF_PLACA`/`UF_INFRACAO`**: apenas 27 UFs aceitas; inválidas viram `NULL` (3,941,160 células corrigidas no total).

---
Leitura: `read_parquet('dados_tratados/base_analitica/*.parquet')` (DuckDB/pandas).
