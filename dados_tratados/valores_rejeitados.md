# valores_rejeitados — o que foi considerado nulo/incorreto na padronização

Lista detalhada das células que `scripts/04_tratar.py` converteu para `NULL` e que compõem os totais do `resumo_colunas.md` §3. Obtida por varredura direta dos 19 `.csv.gz` de `dados_brutos/` (fonte pré-padronização).

- **UF de placa inválidas → `NULL`: 3,941,160** células (bate exatamente com o §3 do resumo)
- **`ESPECIE` sentinela → `NULL`: 7,831,550** células (bate exatamente com o §3 do resumo)

## 1. Regras aplicadas (catálogo completo)

**Todas as colunas de texto** — qualquer valor igual a (maiúsculo, após `TRIM`):

`'-1` · `-1` · `NA` · `N/A` · `N/I` · `N-I` · `N-A` · `NULL` · `NULO` · `#N/A` → **`NULL`**

Também `NULL`: vazio/`TRIM`→vazio; e nas regras específicas:

| Regra | Resultado | Células corrigidas (19 anos) |
|-------|-----------|------------------------------:|
| `UF_PLACA`/`UF_INFRACAO` fora das 27 UFs válidas | `NULL` | **3,941,160** (só placa; infra = 0) |
| `ESPECIE` com sentinela | `NULL` | **7,831,550** |
| Data fora de ISO/`DD/MM/AAAA` ou fora de 2007–2025 | `NULL` | 0 |
| `HORA` não convertível em `TIME` | `NULL` | 0 |
| `NUM_KM_INFRACAO` não numérico ou negativo | `NULL` | 0 |
| `QTD_INFRACOES` não numérico ou `<= 0` | `NULL` | 0 |
| `NUM_BR_INFRACAO` não numérico | `NULL` | 0 |
| `ANO` divergente do ano da `DATA_INFRACAO` | (reportado) | 0 |

## 2. `UF_PLACA` — valores inválidos (108 distintos)

### Por ano

| Ano | Células |
|----:|--------:|
| 2009 | 1 |
| 2011 | 1 |
| 2013 | 1,267 |
| 2014 | 13 |
| 2019 | 1,112,328 |
| 2020 | 95,164 |
| 2022 | 875,441 |
| 2023 | 1,071,395 |
| 2024 | 762,438 |
| 2025 | 23,112 |
| **Total** | **3,941,160** |

### Por valor (ordem decrescente)

| Valor bruto | Células |
|-------------|--------:|
| `'-1` | 2,553,720 |
| `-1` | 1,361,628 |
| `9B` | 10,449 |
| `/` | 4,812 |
| `9C` | 3,605 |
| `93` | 1,402 |
| `95` | 1,025 |
| `8A` | 956 |
| `99` | 452 |
| `9A` | 328 |
| `00` | 311 |
| `98` | 308 |
| `34` | 172 |
| `94` | 167 |
| `07` | 117 |
| `65` | 107 |
| `02` | 94 |
| `67` | 73 |
| `01` | 71 |
| `35` | 71 |
| `23` | 61 |
| `91` | 58 |
| `77` | 57 |
| `3N` | 53 |
| `33` | 51 |
| `27` | 49 |
| `05` | 48 |
| `25` | 47 |
| `3V` | 45 |
| `9E` | 44 |
| `71` | 38 |
| `3C` | 36 |
| `89` | 33 |
| `85` | 31 |
| `3F` | 28 |
| `97` | 27 |
| `30` | 24 |
| `83` | 23 |
| `75` | 23 |
| `79` | 22 |
| `96` | 22 |
| `3G` | 22 |
| `57` | 20 |
| `8B` | 20 |
| `81` | 19 |
| `51` | 18 |
| `53` | 18 |
| `13` | 18 |
| `9U` | 18 |
| `47` | 17 |
| `61` | 17 |
| `11` | 15 |
| `41` | 15 |
| `73` | 14 |
| `03` | 14 |
| `45` | 12 |
| `31` | 12 |
| `63` | 12 |
| `37` | 10 |
| `19` | 10 |
| `69` | 10 |
| `87` | 10 |
| `15` | 9 |
| `59` | 9 |
| `04` | 9 |
| `39` | 8 |
| `32` | 8 |
| `43` | 7 |
| `09` | 7 |
| `2F` | 7 |
| `55` | 6 |
| `17` | 6 |
| `29` | 5 |
| `1C` | 5 |
| `21` | 4 |
| `KN` | 4 |
| `3H` | 4 |
| `66` | 4 |
| `9V` | 4 |
| `49` | 3 |
| `WV` | 3 |
| `8C` | 3 |
| `2G` | 3 |
| `18` | 3 |
| `80` | 2 |
| `64` | 2 |
| `12` | 2 |
| `2H` | 2 |
| `62` | 2 |
| `40` | 2 |
| `36` | 1 |
| `84` | 1 |
| `86` | 1 |
| `74` | 1 |
| `LH` | 1 |
| `LL` | 1 |
| `10` | 1 |
| `6G` | 1 |
| `5N` | 1 |
| `0J` | 1 |
| `5P` | 1 |
| `3K` | 1 |
| `3D` | 1 |
| `2S` | 1 |
| `5C` | 1 |
| `78` | 1 |
| `26` | 1 |
| `1H` | 1 |

Leitura: `'-1`/`-1` são sentinelas de "não informado" da fonte (era2/3); os demais (`9B`, `/`, `9C`, dígitos soltos…) são lixo de digitação/fragmentos de placa — todos viram `NULL`, nunca UF inventada.

## 3. `ESPECIE` — sentinelas (2 distintos)

| Valor bruto | Células | Anos |
|-------------|--------:|------|
| `'-1` | 4,804,523 | 2020, 2021, 2022, 2023 |
| `-1` | 3,027,027 | 2019 |
| **Total** | **7,831,550** | 2019–2023 |

Só a era2 (2019–2021 + resíduos em 2022–23) usa esses marcadores; era1 não tem `ESPECIE` sentinela e era3 (2024–25) já traz valores reais (`PASSAGEIRO`, `CARGA`…).

---
Gerado da varredura da fonte em 2026-11-25; totais conferem com `resumo_colunas.md` §3 e com `dados_tratados/_validacao.jsonl`.
