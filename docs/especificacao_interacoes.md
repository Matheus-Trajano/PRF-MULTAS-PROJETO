# Especificação de interações (Etapa D) — Fase 3

Como o usuário navega nos gráficos Plotly. Aplica-se ao notebook `05_eda_plotly.ipynb`
e futuramente ao Dash.

## 1. Cascata temporal (pedido do usuário)

```
[ANO] ──clique──▶ [MÊS] ──clique──▶ [SEMANA] ──clique──▶ [DIA]
  ▲                   ▲                   ▲                  │
  └───── voltar ◀─────┴───── voltar ◀─────┴───── voltar ◀────┘
```

1. **Estado atual** representado por um *breadcrumb* (`2024 › MARCO › SEMANA 2 › 2024-03-15`);
2. **Clique** numa barra/ponto = drill: filtra o próximo nível e redesenha;
3. **Botão "voltar"** (ou clique no breadcrumb) sobe um nível — nada é destruído,
   apenas o filtro muda;
4. Em qualquer nível os demais painéis (top10, mapa, natureza) respeitam o filtro;
5. Níveis usam os agregados: `tempo_diario` (ano/mês/semana/dia) e `hora_diaria`
   (selecionando um dia → heatmap hora daquele dia).
6. No `05_eda_plotly.ipynb` (Etapa E) a cascata é operada por **seletores
   Mês/Semana + breadcrumb** (clique em barra fica para o Dash — E2);
   a lógica de níveis é exatamente a especificada acima.

Hierarquias paralelas com o mesmo mecanismo:
- `ANO → QUARTIL → MES` (H3);
- `UF → MUNICÍPIO` (H4); `NATUREZA → DESCRIÇÃO` (H4); `ESPECIE → TIPO → MARCA` (H5).

## 2. Filtros globais (barra fixa)

| Filtro | Origem | Efeito |
|--------|--------|--------|
| Ano (múltiplo) | `ANO` em todos os agregados | todos os painéis |
| UF de ocorrência | `UF_INFRACAO` (em TODOS os 12 agregados desde a Etapa B) | todos os painéis |
| Município | `NOM_MUNICIPIO` (`top_municipio`) | geografia (drill do treemap UF→município) |
| Natureza | `NATUREZA_INFRA` (`natureza`, `top_infracao`) | infração + demais |
| Período livre | rango sobre `DATA_INFRACAO` (`tempo_diario`) | temporal + demais |

Regras:
- filtros são **aditivos** (ANO ∩ UF ∩ natureza…);
- todo filtro visível com botão **"limpar"**;
- mudanças re-renderizam **todos** os gráficos na mesma seleção (sincronia).

## 3. NULL / "NÃO INFORMADO"

- Qualquer dimensão com `NULL` vira categoria rotulada **"NÃO INFORMADO"**
  (ex.: `HORA` em 48% do era1; `TIPO_VEICULO` antes de 2022);
- **Nunca** filtrar NULL silenciosamente — se um filtro exclui NULL, o rótulo some
  do gráfico, não da contagem (barras de total permanecem coerentes: soma = 92.215.588);
- Lacunas de era exibem aviso: *"TIPO_VEICULO só existe a partir de 2022"*.

## 4. Comportamento dos Top10

- Sempre **top10 reativo** ao filtro ativo (mudou o ano → reordena);
- Mostrar valor absoluto **e** % do total filtrado;
- `NOM_MUNICIPIO` sempre rotulado como `UF — MUN` (114 homônimos);
- `NOME_VEICULO_MARCA` sem dicionário ainda → rotular como "grafias da fonte".

## 5. Consumo dos agregados

| Gráfico | Arquivo |
|---------|---------|
| cascata ano→mês→semana→dia | `agregados/tempo_diario.parquet` |
| heatmap dia×hora, turnos | `agregados/hora_diaria.parquet` |
| top10 multas / treemap | `top_infracao`, `natureza` |
| top10 BR / UF / município | `top_br`, `top_uf`, `top_municipio` |
| sankey origem→ocorrência | `origem_ocorrencia` |
| espécie/tipo/marca | `veiculo_especie`, `veiculo_marca` |
| abordagem / lote | `abordagem` |
| velocidade | `velocidade_faixa` |

Todos com `SUM(qtd)` — validação: soma total = 92.215.588 em cada arquivo.
