# dados_tratados — base analítica (Fases 2–3)

Saída de [`scripts/04_tratar.py`](../scripts/04_tratar.py): le os 19 CSV normalizados de
`dados_brutos/` e produz a **base analítica** padronizada.

## Arquivos

| Arquivo | Conteúdo |
|---------|----------|
| `base_analitica/infracoes_YYYY.parquet` | 19 Parquets (ZSTD), **92.215.588 linhas × 28 colunas** — 1 por ano |
| `resumo_colunas.md` | Estatísticas por coluna, nulos por era, anomalias corrigidas e **resumo das colunas que podem/precisam ser resumidas** |
| `valores_rejeitados.md` | **Lista detalhada** do que foi considerado nulo/incorreto (regras + valores brutos com contagem por ano) |
| `agregados/*.parquet` | **12 agregados leves** p/ os gráficos (Etapa B) — fora do Git |

Os `.parquet` são dados grandes → fora do Git (`.gitignore`); regeneração:
`.venv/bin/python scripts/04_tratar.py`.

## Ler

```sql
-- DuckDB
SELECT * FROM read_parquet('dados_tratados/base_analitica/*.parquet');
-- pandas
import pandas as pd; pd.read_parquet('dados_tratados/base_analitica/infracoes_2024.parquet')
```

## Padronização aplicada (todas as 25 colunas de origem)

- **Nomes das colunas: MAIÚSCULOS.**
- Texto: sentinela de origem (`'-1`, `-1`, `NA`, `N/A`, `N/I`, `N-I`, `N-A`, `NULL`, `NULO`) → `NULL`;
  senão `TRIM` + **MAIÚSCULAS** + acentos→ASCII (corrige `TRAÇÃO`×`TRACAO` etc.); vazio → `NULL`.
- `DATA_INFRACAO`, `DATA_INICIO_VIGENCIA`, `DATA_FIM_VIGENCIA` → `DATE` (ISO; `DD/MM/AAAA` defensivo; inválida → `NULL`).
- `HORA` → `TIME` · `NUM_KM_INFRACAO` → `DOUBLE` (aceita vírgula; negativo → `NULL`) ·
  `QTD_INFRACOES` → `BIGINT` (`<=0` → `NULL`) · `NUM_BR_INFRACAO` → `BIGINT` ·
  `UF_PLACA`/`UF_INFRACAO` → apenas 27 UFs válidas (resto → `NULL`) · `COD_INFRACAO` mantido como código (texto).
- Nenhuma linha removida: **92.215.588 entram e saem**.

## Colunas derivadas (novas)

| Coluna | Tipo | Regra |
|--------|------|-------|
| `MES` | VARCHAR | **nome do mês** de `DATA_INFRACAO`: JANEIRO…DEZEMBRO (acento→ASCII: `MARCO`) |
| `ANO` | SMALLINT | ano de `DATA_INFRACAO` |
| `QUARTIL` | VARCHAR | `Q1`=jan-mar · `Q2`=abr-jun · `Q3`=jul-set · `Q4`=out-dez |

Total: **28 colunas**.

## Enriquecimento (Etapa A — `scripts/05_enriquecer.py`)

Relê os 19 Parquets e regrava `base_analitica/` com **37 colunas** (28 + 9 derivadas),
validando in==out ano a ano:

| Coluna | Regra |
|--------|-------|
| `SEMANA_DO_MES` | `((DAY-1)/7)+1` → 1..5 |
| `DIA_SEMANA` | `dayname` EN→PT-ASCII: SEGUNDA…DOMINGO |
| `DIA_SEMANA_NUM` | 1=SEG … 7=DOM |
| `FIM_DE_SEMANA` | SIM (SÁB/DOM) / NAO · NULL se `DATA_INFRACAO` NULL |
| `TURNO` | MADRUGADA 00-05 · MANHA 06-11 · TARDE 12-17 · NOITE 18-23 |
| `FAIXA_HORARIA` | 00-05 / 06-11 / 12-17 / 18-23 |
| `BR_FORMATADA` | `'BR-' \| lpad(NUM_BR,3,'0')` → `BR-116` |
| `CHAVE_LOCALIDADE` | `UF_INFRACAO \| '\|' \| NOM_MUNICIPIO` |
| `NATUREZA_INFRA` | heurística v1 por keyword: VELOCIDADE, ALCOOL_DROGAS, DOCUMENTACAO, TRANSITO, SEGURANCA, ESTACIONAMENTO, VEICULO_EQUIPAMENTO, OUTRAS |

Saneamentos: `NUM_KM_INFRACAO > 5000` → NULL · `NUM_BR_INFRACAO` ∉ 1..999 → NULL.
Log por ano: `_enriquecimento.jsonl` (fora do Git).

## Agregados (Etapa B — `scripts/06_agregar.py`)

`agregados/*.parquet` — 12 tabelas leves para os gráficos (NUNCA as 92 M linhas no
browser). Todas têm `qtd` (count), `ANO` e `UF_INFRACAO`; **soma(qtd) = 92.215.588
em todos** (assert no script):

| Arquivo | Linhas | Arquivo | Linhas |
|---------|-------:|---------|-------:|
| `tempo_diario` | 185.532 | `top_municipio` | 38.188 |
| `hora_diaria` | 1.940.987 | `origem_ocorrencia` | 13.310 |
| `top_infracao` | 136.577 | `natureza` | 4.104 |
| `top_br` | 4.681 | `veiculo_especie` | 8.632 |
| `top_uf` | 513 | `veiculo_marca` | 623.638 |
| `abordagem` | 4.008 | `velocidade_faixa` | 2.220 |

Regeneração: `05_enriquecer.py` → `06_agregar.py` (minutos). Fora do Git.
