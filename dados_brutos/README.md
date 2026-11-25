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

## Regeneração (do zero)

Fontes no Google Drive: pasta `PRF_MULTAS` (RARs 2007–2017) e `Multas_Part` (ZIPs mensais
2018–2025, todos < 100 MB).

```bash
python3 -m venv .venv && .venv/bin/pip install duckdb
npm install node-unrar-js 7zip-bin && chmod +x node_modules/7zip-bin/linux/x64/7za
# 1) baixar as 32 fontes do Drive para google_drive/
node scripts/extract_rar.js google_drive/infracoes_2007.rar google_drive/_extracted/2007  # … 2007–2017
.venv/bin/python scripts/01_unificar_anos.py 2007 … 2017
rm -rf google_drive/_extracted google_drive/*.rar            # libera disco
.venv/bin/python scripts/02_extrair_unificar.py 2018 … 2025   # zips apagados após validação
gzip -6 dados_brutos/infracoes_*.csv                          # libera disco p/ normalização
.venv/bin/python scripts/03_normalizar.py                     # normaliza (lê .csv.gz)
gzip -6 dados_brutos/infracoes_*.csv && cd dados_brutos && sha256sum infracoes_*.csv.gz > SHA256SUMS.txt
```

Detalhes: [`logs/ingestao_multas.md`](../logs/ingestao_multas.md).
