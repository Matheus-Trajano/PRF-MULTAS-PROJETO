# dados_tratados — base analítica (Fase 2)

Saída de [`scripts/04_tratar.py`](../scripts/04_tratar.py): le os 19 CSV normalizados de
`dados_brutos/` e produz a **base analítica** padronizada.

## Arquivos

| Arquivo | Conteúdo |
|---------|----------|
| `base_analitica/infracoes_YYYY.parquet` | 19 Parquets (ZSTD), **92.215.588 linhas × 28 colunas** — 1 por ano |
| `resumo_colunas.md` | Estatísticas por coluna, nulos por era, anomalias corrigidas e **resumo das colunas que podem/precisam ser resumidas** |

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
| `MES` | SMALLINT | mês de `DATA_INFRACAO` (1–12) |
| `ANO` | SMALLINT | ano de `DATA_INFRACAO` |
| `QUARTIL` | VARCHAR | `Q1`=jan-mar · `Q2`=abr-jun · `Q3`=jul-set · `Q4`=out-dez |

Total: **28 colunas**.
