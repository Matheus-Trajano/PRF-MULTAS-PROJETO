# Log de Ingestão — Multas PRF (2007–2025)

Data: 2026-11-24
Etapa: 01 — Unificação de CSVs mensais/bimestrais → **1 arquivo por ano**
Motor: Python 3.11 + DuckDB 2.0.1 (`import duckdb`) — SQL embutido no pipeline Python

## Fonte (Google Drive)

| Pasta | IDs | Conteúdo |
|---|---|---|
| `PRF_MULTAS` | `1jO822dIO44HsxZiyPZWFGMaY-az7x-yz` | 19 compactados originais (2007–2025), todos > 100 MiB |
| `Multas_Part` | `1lIOo7YgJA8cCJakBc0SSjILSlH4nJJfa` | ZIPs mensais pré-particionados pelo usuário (< 100 MB) — 2018–2025 |

- 2007–2017: `.rar` extraídos com `node-unrar-js` (WASM)
- 2018–2025: ZIPs do `Multas_Part` extraídos em `google_drive/_tmp/`
- Download: `google_drive_connector.download_file` (última ferramenta de download; sem curl/egress)

## Processo

### `scripts/01_unificar_anos.py` (2007–2017, final)
1. Ordem cronológica explícita: bimestres (2007–2014) ou meses (2015–2017)
2. Assert de cabeçalho idêntico dentro do ano (md5)
3. Detecção automática de encoding (utf-8; fallback latin-1 — usado só em 2017)
4. `read_csv` com `all_varchar=true` (não infere tipos — tratamento na etapa 02)
5. `COPY ... TO` → `dados_brutos/infracoes_<ANO>.csv`
6. Validação: contagem de entrada == contagem de saída (obrigatória)

### `scripts/02_extrair_unificar.py` (2018–2025, final)
1. Descobre os CSVs mensais dentro de cada ZIP de `google_drive/` (aceita padrões `infraçoes_YYYY_MM.csv`, `infracoes_YYYY_MM.csv`, `jan.csv`)
2. Detecta codec por arquivo (`utf-8` → `utf-8-sig` p/ CSVs com BOM; `latin-1` p/ `infraçoes2020_12`, `2021_12` e `2022_07`); `detect_encoding` só como fallback
3. **`sanear_aspas`**: corrige linhas com nº ímpar de aspas na origem (padrão: modelo sem aspa antes da km). Ocorreu **1×** em toda a base (`infraçoes2024_12b.csv`, linha 195138 → `"VERSA 16 UNIQUE XXX;58197;"` corrigido para `"VERSA 16 UNIQUE XXX";58197;"`); sem a correção o DuckDB fundia linhas e estourava `max_line_size`
4. Validação prévia: nº de campos do primeiro registro de cada mês == nº de colunas do cabeçalho do ano (aborta divergência)
5. Concatenação byte-a-byte em `dados_brutos/infracoes_<ANO>.csv` (só o cabeçalho da 1ª)
6. Validação: contagem DuckDB dos meses == contagem do arquivo final
7. **`union_by_name=true`** obrigatório para 2020 (janeiro tem coluna extra `UF Placa`); todos os demais anos exige cabeçalho idêntico
8. Apaga o ZIP só após a validação do ano

## Resultado (validado — contagem física de linhas == contagem DuckDB em TODOS os anos)

| Ano | Arquivos-fonte | Registros | Colunas | Delim | Encoding | Saída |
|-----|----------------|-----------|---------|-------|----------|-------|
| 2007 | 6 bimestres | 1.855.460 | 20 | `,` | utf-8+BOM | infracoes_2007.csv (311 MB) |
| 2008 | 6 bimestres | 2.432.797 | 20 | `,` | utf-8+BOM | infracoes_2008.csv (423 MB) |
| 2009 | 6 bimestres | 3.045.607 | 20 | `,` | utf-8+BOM | infracoes_2009.csv (534 MB) |
| 2010 | 6 bimestres | 3.038.357 | 20 | `,` | utf-8+BOM | infracoes_2010.csv (532 MB) |
| 2011 | 6 bimestres | 2.884.305 | 20 | `,` | utf-8+BOM | infracoes_2011.csv (502 MB) |
| 2012 | 6 bimestres | 2.843.728 | 20 | `,` | utf-8+BOM | infracoes_2012.csv (495 MB) |
| 2013 | 6 bimestres | 3.251.800 | 20 | `,` | utf-8+BOM | infracoes_2013.csv (572 MB) |
| 2014 | 6 bimestres | 3.327.193 | 20 | `,` | utf-8+BOM | infracoes_2014.csv (588 MB) |
| 2015 | 12 meses | 5.408.986 | 21 | `,` | utf-8+BOM | infracoes_2015.csv (1.010 MB) |
| 2016 | 12 meses | 5.584.915 | 21 | `,` | utf-8+BOM | infracoes_2016.csv (1.031 MB) |
| 2017 | 12 meses | 6.023.833 | 22 | `,` | **latin-1** | infracoes_2017.csv (1.132 MB) |
| 2018 | 1 zip, 12 meses | 7.356.159 | 22 | `,` | utf-8+BOM | infracoes_2018.csv (1.622 MB) |
| 2019 | 2 zips, 12 meses | 5.742.110 | 22 | `;` | utf-8+BOM | infracoes_2019.csv (1.073 MB) |
| 2020 | 2 zips, 12 meses | 5.182.537 | **23** | `;` | latin-1* | infracoes_2020.csv (1.057 MB) |
| 2021 | 2 zips, 12 meses | 5.241.299 | 22 | `;` | latin-1* | infracoes_2021.csv (1.172 MB) |
| 2022 | 2 zips, 12 meses | 4.135.523 | 25 | `;` | latin-1* | infracoes_2022.csv (938 MB) |
| 2023 | 3 zips, 12 meses | 5.946.483 | 25 | `;` | utf-8 | infracoes_2023.csv (1.559 MB) |
| **2024** | 4 zips, **11 meses** | 8.710.022 | 25 | `;` | utf-8 | infracoes_2024.csv (2.263 MB) — **INCOMPLETO** |
| 2025 | 4 zips, 12 meses | 10.204.474 | 25 | `;` | utf-8 | infracoes_2025.csv (2.588 MB) |
| **TOTAL** | | **92.215.588** | — | — | — | **~19 GB** |

\* 2020–2022: quase todos os meses latin-1; `2018`/`2019`/`2023`/`2024`/`2025` utf-8 (com BOM tratado na leitura).

## Evolução de schema (cabeçalhos idênticos dentro do ano; exceção 2020)
- 2007–2014: 20 colunas
- 2015–2016: 21 colunas — acrescima de `hora`
- 2017–2019: 22 colunas — acrescima de `cod_infracao`, `nome_veiculo_marca`/`nom_modelo_veiculo`
- 2020: 23 colunas — **`infraçoes2020_1.csv` tem `UF Placa` extra** (union_by_name resolve)
- 2021: 22 colunas
- 2022–2025: 25 colunas

## Achados relevantes (para a etapa 02 de tratamento)
1. **`infraçoes2020_1.csv` (janeiro) tem a coluna `UF Placa`** que os demais meses não têm → schema canônico 2020 = 23 colunas; em tratamento, mapear `UF Placa` para a coluna `uf_placa` quando existir.
2. **Quebra de encoding ao vivo**: `latin-1` em `2020_12`, `2021_12`, `2022_07`, `2017` e quase tudo 2020–2021; utf-8 nos anos 2018, 2019, 2023–2025 (com BOM). Codificação por arquivo já resolvida na ingestão.
3. **1 linha corrompida** em `infraçoes2024_12b.csv` (aspas ímpares) — corrigida por `sanear_aspas`; vale conferir se o modelo/valor corrigido faz sentido no tratamento.
4. **2020 é `union_by_name`**: janeiro tem colunas na ordem diferente + `UF Placa` → em tratamento, alinhar por nome e preencher `uf_placa` ausente com nulo.
5. **junho/2024 está ausente** (11 meses em 2024) — usuário precisa exportar o mês de junho/2024 do RAR e subir como zip < 100 MB antes do tratamento.
6. Colunas-chave do tratamento (referência `Projeto_PRF/sql/modulo03.sql`): `uf`, `municipio`, `br`, `km`, `data_infracao`, `data_hora_infracao`, `natureza`, `especie`, `grau_gravidade`, `orgao`, `enquadramento`, `valor_multa`, `valor_autuacao`, `qtd_ait`, `qtd_ait_gravada`, `tipo_veiculo`, `marca_veiculo`, `modelo_veiculo`, `cnpj_orgao`, `placa`, `uf_placa`, `chassi`, `restricao`, `uf_frota`, `infrator` (ver dicionário do projeto de referência).
7. `all_varchar=true` na ingestão: todos os campos entram como string; tipagem/cast é responsabilidade da etapa 02 (tratamento).

## Pendências / próximos passos
- **junho/2024**: exportar do RAR original (`infraçoes2024_06.csv`) → zip < 100 MB → Drive (`Multas_Part` ou pasta nova) → rodar `scripts/02_extrair_unificar.py 2024` de novo (sobrescreve o arquivo do ano).
- **Etapa 02 (tratamento/padronização)**: `dados_tratados/` com base analítica + base modelável (espelhando `Projeto_PRF` do FAP-2026).
- Encoding/colunas do tratamento: seguir `sql/modulo03.sql` (`read_csv(..., sample_size=-1, all_varchar=true)`, `COPY` utf-8 com `;`) e `src/modulo04_*` (dicionário, nulos → `IGNORADO`, etc.).
