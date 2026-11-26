# dados_brutos — Multas PRF (2007–2025)

**19 CSVs unificados** (um por ano), **normalizados** com schema canônico único de 25 colunas.
Total: **92.215.588 registros** (≈ 17,9 GB em CSV; **2,26 GB comprimidos**).

> ⚠️ Os `.csv` têm de 319 MB a 2,26 GB — **acima do limite de 100 MB por arquivo do GitHub**.
> Por isso este diretório guarda os dados **compactados (gzip)** e os maiores que 95 MB
> **particionados em volumes** (`.aa`, `.ab`, …). Remontagem, validação e uso abaixo.

## Download e remontagem

```bash
# 1) baixar os arquivos de dados_brutos/ (sparse-checkout do repo, ou cada parte via raw):
#    https://github.com/Matheus-Trajano/PRF-MULTAS-PROJETO/raw/arena/1be68652-prf-multas-projeto/dados_brutos/<arquivo>

# 2) anos particionados (2015–2025): remontar o .gz
cat infracoes_2025.csv.gz.* > infracoes_2025.csv.gz

# 3) validar integridade (SHA-256 dos .gz completos)
sha256sum -c SHA256SUMS.txt

# 4) descompactar -> infracoes_2025.csv   (2007–2014 já vêm como .gz único, sem remontagem)
gunzip infracoes_2025.csv.gz
```

O DuckDB lê direto do comprimido, sem descompactar:
`SELECT * FROM read_csv('infracoes_2007.csv.gz', header=true, delim=';', all_varchar=true)`.

O DuckDB lê direto do comprimido, sem descompactar:
`SELECT * FROM read_csv('infracoes_2007.csv.gz', header=true, delim=';', all_varchar=true)`.

## Arquivos

| Ano | Registros | CSV | `.csv.gz` no Git |
|-----|-----------|-----|---------------------|
| 2007 | 1.855.460 | 319 MB | 30,5 MB |
| 2008 | 2.432.797 | 435 MB | 43,7 MB |
| 2009 | 3.045.607 | 548 MB | 57,8 MB |
| 2010 | 3.038.357 | 546 MB | 57,6 MB |
| 2011 | 2.884.305 | 516 MB | 55,1 MB |
| 2012 | 2.843.728 | 509 MB | 54,1 MB |
| 2013 | 3.251.800 | 585 MB | 61,7 MB |
| 2014 | 3.327.193 | 603 MB | 61,4 MB |
| 2015 | 5.408.986 | 1.030 MB | 115,9 MB |
| 2016 | 5.584.915 | 1.051 MB | 123,1 MB |
| 2017 | 6.023.833 | 1.134 MB | 132,0 MB |
| 2018 | 7.356.159 | 1.370 MB | 162,0 MB |
| 2019 | 5.742.110 | 1.120 MB | 137,1 MB |
| 2020 | 5.182.537 | 978 MB | 120,6 MB |
| 2021 | 5.241.299 | 999 MB | 123,0 MB |
| 2022 | 4.135.523 | 961 MB | 147,5 MB |
| 2023 | 5.946.483 | 1.385 MB | 209,6 MB |
| 2024 | 8.710.022 | 2.006 MB | 294,4 MB |
| 2025 | 10.204.474 | 2.245 MB | 329,9 MB |
| **Total** | **92.215.588** | **≈ 17,9 GB** | **2,26 GB** |

Integridade: `SHA256SUMS.txt` (este diretório). Validado por ano: contagem física de linhas ==
`count(*)` do DuckDB == tabela acima; cabeçalho idêntico nos 19 anos (md5 `8fe1a7bb…`).

## Schema canônico (25 colunas, delim `;`, UTF-8, datas ISO `AAAA-MM-DD`, hora `HH:MM:SS`)

`numero_auto, data_infracao, hora, tip_abordagem, ind_assinou_auto, ind_veiculo_estrangeiro,
sentido_trafego, uf_placa, uf_infracao, num_br_infracao, num_km_infracao, nom_municipio,
cod_infracao, descricao_abreviada, enquadramento, data_inicio_vigencia, data_fim_vigencia,
med_realizada, med_considerada, exc_verificado, especie, nome_veiculo_marca, nom_modelo_veiculo,
tipo_veiculo, qtd_infracoes`

Colunas ausentes em uma era ficam vazias nos anos daquela era (ex.: `numero_auto` só 2019+,
`tipo_veiculo` só 2022+, `hora` só 2015+, `qtd_infracoes` só 2020+). Tokens de ausência de origem
(`NA`, `N/I`, `N/A`) convertidos para vazio. **jun/2024 não existe na base** — 2024 tem 11 meses.

## Ingestão (fluxo atual — sem Google Drive)

A ingestão parte **destes próprios `.csv.gz`** (fonte única; sem RAR, sem ZIP, sem Drive):

```bash
.venv/bin/python scripts/01_ingestao_brutos.py            # valida os 19 (~1 min)
.venv/bin/python scripts/01_ingestao_brutos.py --sha256   # + integridade (SHA256SUMS.txt)
# em seguida (Fase 2):
.venv/bin/python scripts/04_tratar.py                     # base analítica (~1 h)
```

`01_ingestao_brutos.py` confere por ano: arquivo presente, contagem de linhas
(vs tabela acima), header canônico de 25 colunas e — com `--sha256` — o hash de
`SHA256SUMS.txt`; no fim exige o total **92.215.588**.

## Regeneração das fontes brutas (histórico)

Os CSVs foram gerados originalmente a partir do **Google Drive** (RARs 2007–2017,
ZIPs 2018–2025) com `extract_rar.js` + `01_unificar_anos` + `02_extrair_unificar` —
scripts **removidos** em 2026-11-26; a receita completa ficou registrada em
[`logs/ingestao_multas.md`](../logs/ingestao_multas.md).
