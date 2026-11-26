# Catálogo de gráficos (Etapa C) — Fase 3

Mapeia cada variável de `docs/analise_variaveis.md` §2.1 → tipo de gráfico → métrica →
ordenação → tratamento de NULL. **Fonte de dados:** `dados_tratados/agregados/*.parquet`
(Etapa B) — nunca as 92 M linhas direto no browser. Todos os 13 agregados
carregam `ANO` + `UF_INFRACAO` (filtros globais da Etapa D).

Regra geral de NULL: exibir como categoria **"NÃO INFORMADO"** (nunca ocultar);
`qtd` = contagem de multas (soma sempre = 92.215.588 no total geral).

## 1. Temporal

| Variável | Gráfico | Métrica | Ordenação | Drill | Arquivo |
|----------|---------|---------|-----------|-------|---------|
| `ANO` | linha (evolução) | `SUM(qtd)` | cronológica | clicar ano → meses | `tempo_diario` |
| `MES` | barras | `SUM(qtd)` | ordem natural JANEIRO→DEZEMBRO | clicar mês → semanas | `tempo_diario` |
| `SEMANA_DO_MES` | barras | `SUM(qtd)` | 1→5 | clicar semana → dias | `tempo_diario` |
| `DIA` (`DATA_INFRACAO`) | barras / linha diária | `SUM(qtd)` | cronológica | folha da cascata | `tempo_diario` |
| `DIA_SEMANA` | barras | `SUM(qtd)` | SEG→DOM (`DIA_SEMANA_NUM`) | — | `tempo_diario` |
| `FIM_DE_SEMANA` | pizza/barra dupla | `SUM(qtd)` | SIM, NAO | — | `tempo_diario` |
| `QUARTIL` | barras | `SUM(qtd)` | Q1→Q4 | → meses | `tempo_diario` |
| `HORA` | histograma (00–23) | `SUM(qtd)` | 0→23 | — | `hora_diaria` |
| `TURNO` | barras | `SUM(qtd)` | MADRUGADA→NOITE | — | `hora_diaria` |
| `FAIXA_HORARIA` | barras / heatmap eixo | `SUM(qtd)` | 00-05→18-23 | — | `hora_diaria` |
| **heatmap dia × hora** | `heatmap` | `SUM(qtd)` | data × hora | clicar célula → dia | `hora_diaria` |

## 2. Geográfica

| Variável | Gráfico | Métrica | Ordenação | Drill | Arquivo |
|----------|---------|---------|-----------|-------|---------|
| `UF_INFRACAO` top10 | barras horizontais | `SUM(qtd)` | desc (top10) | clicar UF → municípios | `top_uf` |
| `UF_INFRACAO` mapa | coroplético BR (Dash) · no notebook E: treemap UF→município | `SUM(qtd)` | — | clique = filtro global | `top_uf` |
| `UF_PLACA` top10 | barras | `SUM(qtd)` | desc | — | `origem_ocorrencia` |
| **origem→ocorrência** | sankey / heatmap 27×27 | `SUM(qtd)` | pares por volume | clique par → detalhe | `origem_ocorrencia` |
| `NOM_MUNICIPIO` top10 | barras | `SUM(qtd)` | desc | sempre rotular `UF — MUN` | `top_municipio` |
| `NUM_BR` top10 | barras | `SUM(qtd)` | desc | clicar BR → evolução | `top_br` |
| `BR_FORMATADA` | rótulo (`BR-040`) | — | — | — | `top_br` |
| `NUM_KM` | histograma (faixas de 50 km) + heatmap BR × faixa | `SUM(qtd)` | faixas `000-049`→`1500+`, `NAO_INFORMADO` | clique BR → detalhe | `km_faixa` |
| `SENTIDO_TRAFEGO` | barras | `SUM(qtd)` | C, D | — | `abordagem` |

## 3. Infração

| Variável | Gráfico | Métrica | Ordenação | Drill | Arquivo |
|----------|---------|---------|-----------|-------|---------|
| `DESCRICAO_ABRVIADA` **top10** | barras horizontais | `SUM(qtd)` | desc | → natureza (contexto) | `top_infracao` |
| `ENQUADRAMENTO` | barras top N | `SUM(qtd)` | desc | — | `top_infracao` |
| `NATUREZA_INFRA` | **treemap** / barras | `SUM(qtd)` | desc | natureza → descrição | `natureza`, `top_infracao` |
| evolução por natureza | linhas empilhadas | `SUM(qtd)` por ANO | cronológica | ano → natureza | `natureza` |
| `MED_REALIZADA` | histograma faixas de velocidade | `SUM(qtd)` | faixas 00-40→120+ | — | `velocidade_faixa` |
| `EXC_VERIFICADO` | barras | `SUM(qtd)` | desc | — | fase E |
| `QTD_INFRACOES` | barras avulso×lote | `SUM(qtd)` | — | — | `abordagem` |

## 4. Veículo

| Variável | Gráfico | Métrica | Ordenação | Drill | Arquivo |
|----------|---------|---------|-----------|-------|---------|
| `ESPECIE` | barras | `SUM(qtd)` | desc | espécie → tipo | `veiculo_especie` |
| `TIPO_VEICULO` top10 | barras | `SUM(qtd)` | desc (filtro ≥2022!) | tipo → marca | `veiculo_especie` |
| `NOME_VEICULO_MARCA` top10 | barras | `SUM(qtd)` | desc | — | `veiculo_marca` |
| `IND_VEICULO_ESTRANGEIRO` | barras | `SUM(qtd)` | S, N | — | fase E |

## 5. Abordagem / auto

| Variável | Gráfico | Métrica | Ordenação | Arquivo |
|----------|---------|---------|-----------|---------|
| `TIP_ABORDAGEM` | barras/pizza | `SUM(qtd)` | S, C | `abordagem` |
| `IND_ASSINOU_AUTO` | barras | `SUM(qtd)` | S, N, NÃO INFORMADO | `abordagem` |

## 6. Padrões de interação (Etapa D — ver `docs/especificacao_interacoes.md`)

- Cascata temporal: **ano → mês → semana → dia** (clique + breadcrumb + voltar);
- Filtros globais (ano, UF, natureza) sincronizam todos os painéis;
- Top10 sempre reordenado pelo filtro ativo;
- NULLs visíveis como "NÃO INFORMADO"; períodos com lacuna de era
  (ex.: `TIPO_VEICULO` só 2022+) exibem aviso de cobertura.
