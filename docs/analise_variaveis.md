# Análise — variáveis de interesse para visualização (Fase 3)

> Análise **sem implementação** (etapa de preparação). Base: `dados_tratados/base_analitica`
> (28 col, 92.215.588 linhas) + `resumo_colunas.md` + varreduras diretas da fonte (2026-11-25).

## 1. Estrutura atual (auditoria rápida)

| Ativo | Conteúdo |
|-------|----------|
| `scripts/01–04` | ingestão → normalização (25 col) → base analítica (28 col, Parquet) |
| `dados_brutos/` | 19 CSVs gzip (fonte canônica, checksums) |
| `dados_tratados/base_analitica/` | 19 Parquets · 1,4 GB · **precisa ser regenerado após reset (~1 h, `04_tratar.py`)** |
| `dados_tratados/resumo_colunas.md` | stats por coluna, nulos por era |
| `notebooks/00_pipeline_completo.ipynb` | scripts + validações |
| Cobertura temporal | 2007-01-01 → 2025-12-31, **jun/2024 não existe** (11 meses em 2024) |

**Colunas-chave para gráficos (verificado):**

| Coluna | Distintos | Nulos | Uso |
|--------|----------:|------:|-----|
| `ANO` / `MES` (nome) / `QUARTIL` | 19 / 12 / 4 | 0% | eixo temporal |
| `DATA_INFRACAO` | ~6.940 datas | 0% | base de todas as derivadas temporais |
| `HORA` | 85.475 | **24,6%** (era1 48,2%) | horário / turno |
| `UF_INFRACAO` | **27** (todas as UFs) | 0% | top estados / mapa |
| `UF_PLACA` | ~26 | 15,6% | origem do veículo |
| `NOM_MUNICIPIO` | 3.228 | 0% | top municípios — **114 homônimos em >1 UF** (ex.: BOM JESUS em 5 UFs) |
| `NUM_BR_INFRACAO` | **195** | 3 células | top BRs |
| `NUM_KM_INFRACAO` | — | 0% | trecho — **outlier: máx 9.871 km (sanear)** |
| `DESCRICAO_ABRVIADA` / `ENQUADRAMENTO` | 705 / 564 | **0%** | top multas |
| `COD_INFRACAO` | 410 | **36,5%** (era1 71,6%) | dicionário — evitar em série cheia |
| `ESPECIE` | 10 | 18,6% | barra simples |
| `TIPO_VEICULO` | 89 | 68,6% (**só era3**) | gráficos 2022+ |
| `NOME_VEICULO_MARCA` / `MODELO` | 38.153 / 137.695 | 31,8% / 20,3% | alta cardinalidade → dicionário antes de top10 |
| `TIP_ABORDAGEM` / `SENTIDO_TRAFEGO` | 2 / 3 | 0% / 23,7% | barras |
| `QTD_INFRACOES` | 2 | 57,3% (**era3**) | autos em lote |
| `MED_REALIZADA` / `CONSIDERADA` | 41k / 88k | 29,6% / 19,2% | converter DOUBLE (velocidade) |

## 2. Gap analysis — pedidas × existentes

| Variável pedida | Status | Observação |
|-----------------|--------|------------|
| Multas por mês | ✅ existe | `ANO` × `MES` (nome pronto p/ eixo) |
| Semana do mês com mais multas | ❌ **derivar** | criar `SEMANA_DO_MES` (1–5) de `DATA_INFRACAO` |
| Dia da semana com mais multas | ❌ **derivar** | criar `DIA_SEMANA` (SEG…DOM) + `DIA_SEMANA_NUM` |
| Top 10 de multas | ⚠️ existe | usar `DESCRICAO_ABRVIADA`/`ENQUADRAMENTO` (0% nulo); `COD` só com dicionário (era1 71,6% nulo) |
| Top 10 de BRs | ✅ existe | `NUM_BR_INFRACAO` (195 códigos; 3 nulos) |
| Top 10 de estados | ✅ existe | `UF_INFRACAO` — 27 UFs completas |
| Top 10 de municípios | ⚠️ existe | **chave = `UF_INFRACAO`+`NOM_MUNICIPIO`** (114 homônimos) |
| Horário com mais multas | ⚠️ existe | `HORA` (era1 48% nulo) + derivar `TURNO`/`FAIXA_HORARIA`; nulos viram "NÃO INFORMADO" |

### 2.1 Variáveis por categoria (acréscimo solicitado)

**Temporal** — base de toda a cascata ano→mês→semana→dia:

| Variável | Origem | Tipo | Nulos | Gráfico sugerido |
|----------|--------|------|------:|------------------|
| `ANO` | existe | SMALLINT | 0% | linha de evolução / filtro global |
| `QUARTIL` | existe | VARCHAR Q1–Q4 | 0% | barra / filtro |
| `MES` | existe | VARCHAR nome | 0% | eixo de barras (ordem natural) |
| `SEMANA_DO_MES` | **derivar** (1–5) | SMALLINT | 0% | drill do mês; barra "semana com mais multas" |
| `DIA_SEMANA` / `DIA_SEMANA_NUM` | **derivar** (SEG…DOM) | VARCHAR/SMALLINT | 0% | barras por dia da semana; heatmap |
| `FIM_DE_SEMANA` | **derivar** (sáb/dom) | VARCHAR | 0% | comparativo úteis × fim de semana |
| `DATA_INFRACAO` | existe | DATE | 0% | série diária, drill até o dia |
| `HORA` | existe | TIME | 24,6% | histograma / heatmap hora |
| `TURNO` | **derivar** (MADRUGADA 0–5, MANHÃ 6–11, TARDE 12–17, NOITE 18+) | VARCHAR | = `HORA` | barras por turno |
| `FAIXA_HORARIA` | **derivar** (00–05, 06–11, 12–17, 18–23) | VARCHAR | = `HORA` | heatmap faixa × dia |
| (futuro) `FERIADO` | enriquecimento externo | VARCHAR | — | úteis × feriado × fim de semana |

**Geográfica**

| Variável | Origem | Tipo | Nulos | Gráfico sugerido |
|----------|--------|------|------:|------------------|
| `UF_INFRACAO` | existe | 27 UFs | 0% | **top10 barras + mapa coroplético** |
| `UF_PLACA` | existe | ~26 siglas | 15,6% | top estados de origem |
| par origem→ocorrência | **derivar** `UF_PLACA`→`UF_INFRACAO` | par | — | **sankey / heatmap 27×27** |
| `NOM_MUNICIPIO` | existe | 3.228 | 0% | top10 (sempre com UF) |
| `CHAVE_LOCALIDADE` | **derivar** `UF_INFRACAO`+`NOM_MUNICIPIO` | VARCHAR | 0% | resolve os **114 homônimos** |
| `NUM_BR_INFRACAO` | existe | 195 códigos | 3 células | **top10 BRs** / ranking |
| `BR_FORMATADA` | **derivar** (`BR-###`) | VARCHAR | ≈0 | rótulo de eixo |
| `NUM_KM_INFRACAO` | existe | DOUBLE | 0% (outlier máx 9.871 km → sanear) | distribuição por BR, trecho |
| `SENTIDO_TRAFEGO` | existe | C/D | 23,7% | barras |

**Infração**

| Variável | Origem | Tipo | Nulos | Gráfico sugerido |
|----------|--------|------|------:|------------------|
| `DESCRICAO_ABRVIADA` | existe | 705 textos | **0%** | **top10 multas** (barras horizontais) |
| `ENQUADRAMENTO` | existe | 564 textos | **0%** | top10 / agrupador |
| `COD_INFRACAO` | existe | 410 códigos | 36,5% (era1 71,6%) | dicionário código→texto; série cheia só com descrição |
| `NATUREZA_INFRA` | **derivar** (grupo do código: velocidade, documentação, equipamento…) | VARCHAR | ≈0 | **treemap natureza→descrição**, evolução |
| `MED_REALIZADA` / `MED_CONSIDERADA` | existe | converter DOUBLE | 29,6% / 19,2% | histograma de velocidades, boxplot por BR |
| `EXC_VERIFICADO` | existe | texto | 19,8% | barras |
| `DATA_INICIO/FIM_VIGENCIA` | existe | DATE | 0,08% / 64,8% | vigência da regra (linha do tempo normativa) |
| `QTD_INFRACOES` | existe | BIGINT (era3) | 57,3% | avulso × lote |

**Veículo**

| Variável | Origem | Tipo | Nulos | Gráfico sugerido |
|----------|--------|------|------:|------------------|
| `ESPECIE` | existe | 10 categorias | 18,6% | **barras simples** (PASSAGEIRO, CARGA…) |
| `TIPO_VEICULO` | existe | 89 categorias | 68,6% (**só 2022+**) | top10 com filtro de período |
| `NOME_VEICULO_MARCA` | existe | 38.153 grafias | 31,8% | top10 **após dicionário** de marcas |
| `NOM_MODELO_VEICULO` | existe | 137.695 grafias | 20,3% | top10 após dicionário |
| `MARCA_NORMALIZADA` / `MODELO_NORMALIZADO` | **derivar** (dicionário controlado) | VARCHAR | ≈0 | base dos rankings de marca/modelo |
| `IND_VEICULO_ESTRANGEIRO` | existe | S/N | 0,0% | placa estrangeira × UF |


## 3. Hierarquias de drill-down (design para Plotly)

Pedida pelo usuário (cascata por clique):

```
H1  ANO ──▶ MES ──▶ SEMANA_DO_MES ──▶ DIA          (seleciona ano→vê meses;
H2  ANO ──▶ MES ──▶ DIA_SEMANA                     mes→vê semanas/semana→vê dias)
H3  ANO ──▶ QUARTIL ──▶ MES                        (agregação alternativa)
H4  UF ──▶ MUNICIPIO(+UF)     |  BR ──▶ trecho(KM) |  NATUREZA ──▶ COD/DESCRIÇÃO
H5  ESPECIE ──▶ TIPO_VEICULO ──▶ MARCA* ──▶ MODELO*     (drill de veículo)
```

Regras de interação:
- **Drill por clique** no gráfico (barra/ponto selecionado vira filtro do próximo nível) + botão "voltar";
- **Filtros globais** (ano, UF, natureza…) sincronizam todos os painéis;
- NULLs sempre visíveis como categoria **"NÃO INFORMADO"** (HORA, TIPO_VEICULO…), nunca somem;
- **92 M linhas não vão ao browser** → os gráficos leem uma camada pré-agregada (Etapa B).

## 4. Catálogo de variáveis de interesse (para gráficos futuros)

**A. Temporal** — `ANO`, `MES`, `QUARTIL`, `DIA_SEMANA*`, `SEMANA_DO_MES*`, `FIM_DE_SEMANA*`,
`TURNO*`/`FAIXA_HORARIA*` (MADRUGADA 0–5 / MANHÃ 6–11 / TARDE 12–17 / NOITE 18+).
* gráficos: linha de evolução mensal com drill, barras por dia-semana, heatmap **dia × faixa horária**, sazonalidade (mês × ano).

**B. Infração** — `ENQUADRAMENTO`/`DESCRICAO_ABRVIADA` (top10), `COD_INFRACAO`+dicionário,
grupo `NATUREZA*` (derivar: velocidade, documentação, equipamento…).
* gráficos: barras horizontais top10, treemap natureza→descrição, evolução por natureza.

**C. Geografia** — `UF_INFRACAO` (top10 + **mapa coroplético**), `UF_PLACA` (origem),
**par origem→ocorrência** (sankey / heatmap UF×UF), município (UF+MUN), `NUM_BR` (top10 + ranking de BRs),
`NUM_KM` (distribuição por BR — saneamento de outliers > 5.000 km), `SENTIDO_TRAFEGO`.

**D. Veículo** — `ESPECIE` (barras), `TIPO_VEICULO` (só 2022+ — filtro de período), marca/modelo
(top10 **após** dicionário/normalização — 38 mil grafias), `IND_VEICULO_ESTRANGEIRO`.

**E. Auto/abordagem** — `TIP_ABORDAGEM` (S/C), `IND_ASSINOU_AUTO`, `QTD_INFRACOES` (lote vs avulso),
`NUMERO_AUTO` (métrica de contagem/distintos).

**F. Medidas** — `MED_REALIZADA`/`MED_CONSIDERADA` → converter **DOUBLE** (histograma de velocidades,
boxplot por BR); `EXC_VERIFICADO`.

**G. Métricas (eixos Y)** — `count(*)` de multas, médias de KM/velocidade, distinct de autos.

**H. Limitações a declarar nos dashboards** — não existe coluna de **valor monetário** nem de gravidade;
lacunas de era (`HORA`, `COD`, `TIPO_VEICULO`, `QTD`, `NUMERO_AUTO`); jun/2024 ausente;
KM com outliers; 114 homônimos municipais.

\* = coluna nova a derivar (Etapa A).

## 5. Etapas por partes (plano da Fase 3)

| Etapa | Entrega | Detalhe |
|-------|---------|---------|
| **A. Enriquecimento** | `scripts/05_enriquecer.py` | Derivar `DIA_SEMANA(_NUM)`, `SEMANA_DO_MES`, `FIM_DE_SEMANA`, `TURNO`, `FAIXA_HORARIA`, `BR_FORMATADA` (BR-###), `CHAVE_LOCALIDADE` (UF+MUN), `NATUREZA_INFRA`; saneamentos (KM outliers, BR inválidos). Pré-requisito: regenerar os Parquets (`04_tratar.py`, ~1 h). Validação: 92.215.588 in == out, coerência DATA×derivadas. |
| **B. Camada de agregação** | `dados_tratados/agregados/*.parquet` | Pré-computar as hierarquias H1–H4 (ano×mes×semana×dia × dims) + tops pré-ordenados; motivo: latência e limite do browser. Uma leitura DuckDB/json alimenta o Plotly. |
| **C. Catálogo de gráficos** | documento `docs/catalogo_graficos.md` | Mapear cada variável do §4 → tipo de gráfico, métrica, ordenação, tratamento de NULL. |
| **D. Interações** | spec | Cascata ano→mes→semana→dia (clique + voltar), filtros globais, "NÃO INFORMADO", sincronia entre painéis. |
| **E. Implementação** | `notebooks/05_eda_plotly.ipynb` (→ Dash futuro) | Só após aprovação das etapas A–D; seguir espelho do módulo05 de referência. |

**Ordem de execução recomendada:** A → B → C/D (podem rodar em paralelo) → E.
