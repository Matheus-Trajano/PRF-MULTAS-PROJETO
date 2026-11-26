#!/usr/bin/env python3
"""
_build_graficos.py — monta e executa notebooks/09_parte6_graficos.ipynb
(Parte 6 — Gráficos), no MESMO padrão do repositório de referência
PRF_pandas_plotly-2023-2025:

  - notebook ordenado por etapa (09_parte6_graficos.ipynb);
  - cada gráfico = célula de texto com Pergunta/Resposta + célula de código;
  - título com a mensagem principal + legenda de 2 linhas (`titulo()`);
  - `salvar_grafico(fig, nome)` → resultados/<nome>.html (autocontido) + PNG
    quando há Chrome/kaleido;
  - asserts antes de salvar.

Modo pausado: um gráfico por vez — adicione o par (MD, CODE) em GRAFICOS
e reexecute este script.

Uso: .venv/bin/python notebooks/_build_graficos.py
"""
from __future__ import annotations

from pathlib import Path

import nbformat
from nbclient import NotebookClient

RAIZ = Path(__file__).resolve().parent.parent
NB_DIR = RAIZ / "notebooks"
SAIDA = NB_DIR / "09_parte6_graficos.ipynb"

MD_TITULO = """\
# Parte 6 — Gráficos

**Gráficos com Plotly**, salvos em `resultados/`.

Regras do enunciado, aplicadas a todos:

- cada gráfico **responde a uma pergunta**, escrita na célula de texto imediatamente acima;
- o **título carrega a mensagem principal** (não apenas o nome do gráfico);
- abaixo do título há uma **legenda de 2 linhas** com o que está sendo medido e como ler;
- caminhos **relativos com `Path`** — nada é escrito fora de `resultados/`;
- os arquivos de origem **não são sobrescritos**.

Base: os **19 Parquets** de `dados_tratados/base_analitica/` (2007–2025,
**92.215.588** linhas). A varredura é feita pelo **DuckDB** (`import duckdb`,
regra do projeto) — o pandas só recebe o resultado agregado, nunca as 92 M linhas.

*Sequência pausada: este notebook recebe um gráfico por etapa.*
"""

MD_SETUP = """\
## 0. Base e utilitários

A raiz é localizada subindo os diretórios até achar `dados_tratados/`; o
DuckDB varre a base inteira e devolve o agregado pedido.
"""

CODE_RAIZ = '''\
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import plotly.graph_objects as go


def localizar_raiz() -> Path:
    for candidato in [Path.cwd(), *Path.cwd().parents]:
        if (candidato / "dados_tratados").is_dir():
            return candidato
    raise FileNotFoundError("Abra o notebook da raiz do projeto ou de 'notebooks/'.")


RAIZ = localizar_raiz()
DIR_TRATADOS = RAIZ / "dados_tratados"
DIR_RESULTADOS = RAIZ / "resultados"
DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)

TOTAL_ESPERADO = 92_215_588
BASE = str(DIR_TRATADOS / "base_analitica" / "*.parquet")
print(RAIZ)
'''

CODE_BASE = '''\
con = duckdb.connect(":memory:")
con.execute("SET threads=2")
con.execute("SET memory_limit='1500MB'")

TOTAL = con.execute(f"SELECT COUNT(*) FROM read_parquet('{BASE}')").fetchone()[0]
assert TOTAL == TOTAL_ESPERADO, f"total = {TOTAL:,} != {TOTAL_ESPERADO:,}"

# Top 10 causas juntando TODOS os anos (sem filtro de ANO)
top10 = con.execute(f"""
    SELECT DESCRICAO_ABRVIADA AS causa, COUNT(*) AS multas
    FROM read_parquet('{BASE}')
    GROUP BY 1 ORDER BY 2 DESC LIMIT 10
""").df()
top10["pct"] = 100 * top10["multas"] / TOTAL

print(f"Base: {TOTAL:,} multas (19 bases, 2007–2025) · top10 = "
      f"{top10['multas'].sum():,} ({top10['pct'].sum():.1f}%)")
'''

CODE_UTIL = '''\
CIMA = "#b03a2e"     # causas de velocidade
BAIXO = "#7f8c8d"    # demais causas
NEUTRO = "#2c3e50"
AZUL = "#1f4e79"
BARRA = "#c8d6e5"


def pct(valor: float, casas: int = 2) -> str:
    """Percentual no padrão brasileiro — vírgula como separador decimal."""
    return f"{valor * 100:.{casas}f}%".replace(".", ",")


def br(valor: int) -> str:
    """Inteiro no padrão brasileiro — ponto como separador de milhar."""
    return f"{valor:,}".replace(",", ".")


def titulo(mensagem: str, legenda_l1: str, legenda_l2: str) -> dict:
    """Título com a mensagem principal e a legenda de 2 linhas."""
    return dict(
        text=f"<b>{mensagem}</b><br><sup>{legenda_l1}<br>{legenda_l2}</sup>",
        x=0.01, xanchor="left", y=0.95, yanchor="top", automargin=True,
        font=dict(size=16, color="#1a1a1a"),
    )


def salvar_grafico(fig, nome: str) -> None:
    """Salva o gráfico em `resultados/` — HTML sempre, PNG quando houver Chrome."""
    html = DIR_RESULTADOS / f"{nome}.html"
    fig.write_html(html, include_plotlyjs=True)
    salvos = [html.name]
    try:
        png = DIR_RESULTADOS / f"{nome}.png"
        fig.write_image(png, width=1600, height=900, scale=2)
        salvos.append(png.name)
    except Exception:
        print("PNG não gerado (kaleido precisa de Chrome instalado); HTML salvo.")
    print(f"resultados/: {', '.join(salvos)}")
    fig.show()
'''

MD_G1 = """\
---

## Gráfico 1 — Quais são as 10 causas de multa que mais ocorrem?

**Pergunta:** juntando **todos os anos** (2007–2025), quais são as 10 causas
(`DESCRICAO_ABRVIADA`) com mais autuações e quanto elas concentram?

**Resposta:** a **velocidade** domina o ranking. A causa nº 1 —
*TRANSITAR EM VELOCIDADE SUPERIOR A MAXIMA PERMITIDA EM ATE 20%* — tem
**39.969.111 multas (43,34%)** sozinha; somadas as duas faixas de velocidade
(esta + *…MAIS DE 20% ATE 50%*, 8.000.472), são **52,0%** de todas as multas
das 19 bases. O top10 reúne **66.155.943 autuações — 71,7%** das
**92.215.588** totais. O pódio se fecha com a ultrapassagem em contramão
linha amarela (4.596.887) e a luz baixa em movimento de dia (2.754.829).
"""

CODE_G1 = '''\
g1 = top10.sort_values("multas", ascending=True).reset_index(drop=True)
causas_velocidade = g1["causa"].str.contains("VELOCIDADE")

fig = go.Figure(go.Bar(
    x=g1["multas"],
    y=g1["causa"],
    orientation="h",
    marker_color=[CIMA if v else BAIXO for v in causas_velocidade],
    text=[br(v) for v in g1["multas"]],
    textposition="outside",
    customdata=np.stack([g1["pct"].map(lambda v: pct(v / 100)),
                         g1["pct"].map(lambda v: pct(v / 100, 1))], axis=-1),
    hovertemplate=(
        "<b>%{y}</b><br>Multas: %{x:,.0f}<br>"
        "% do total: %{customdata[1]}<extra></extra>"
    ),
    name="Multas",
))
fig.update_layout(
    title=titulo(
        "Velocidade responde por 52% das multas — as 10 causas mais "
        "autuadas em 19 anos (2007–2025)",
        "Barras: nº de autuações por causa (DESCRICAO_ABRVIADA), todas as "
        "19 bases somadas; ordenadas da maior para a menor; "
        "vermelho = causas de velocidade.",
        f"Top10 = {br(int(g1['multas'].sum()))} multas "
        f"({pct(g1['multas'].sum() / TOTAL, 1)} de {br(TOTAL)}); "
        "sem filtro de ano.",
    ),
    xaxis=dict(title="Nº de multas (autuações)", gridcolor="#e8e8e8"),
    yaxis=dict(title="", automargin=True),
    plot_bgcolor="white", height=640, margin=dict(l=10, r=80, t=120, b=60),
)
fig.update_xaxes(range=[0, g1["multas"].max() * 1.12])

assert len(g1) == 10, f"Esperava 10 causas, veio {len(g1)}"
assert TOTAL == TOTAL_ESPERADO
assert 0.40 < top10["pct"].iloc[0] / 100 < 0.50, "A causa nº 1 deveria estar perto de 43%"
assert 0.70 < g1["multas"].sum() / TOTAL < 0.75, "O top10 deveria concentrar ~72%"

salvar_grafico(fig, "g1_top10_multas")
'''

MD_FECHO = """\
## Fechamento da Parte 6

| Gráfico | Pergunta que responde | Mensagem principal | Arquivo |
|---|---|---|---|
| 1 | Quais são as 10 causas de multa que mais ocorrem? | Velocidade = 52% das multas; top10 concentra 71,7% | `resultados/g1_top10_multas.html` |

HTML **autocontido** (`include_plotlyjs=True` — abre offline, sem CDN), no
mesmo padrão da referência. O PNG é gerado quando há Chrome para o `kaleido`;
sem ele, o notebook avisa no output e segue sem erro.

*Próximos gráficos entram aqui, um por etapa pausada.*
"""


def main() -> None:
    cells = [
        nbformat.v4.new_markdown_cell(MD_TITULO),
        nbformat.v4.new_markdown_cell(MD_SETUP),
        nbformat.v4.new_code_cell(CODE_RAIZ),
        nbformat.v4.new_code_cell(CODE_BASE),
        nbformat.v4.new_code_cell(CODE_UTIL),
        nbformat.v4.new_markdown_cell(MD_G1),
        nbformat.v4.new_code_cell(CODE_G1),
        nbformat.v4.new_markdown_cell(MD_FECHO),
    ]
    nb = nbformat.v4.new_notebook(cells=cells)
    nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python",
                              "name": "python3"}
    print(f"gerando {SAIDA.name} e executando…", flush=True)
    client = NotebookClient(nb, timeout=300, kernel_name="python3",
                            resources={"metadata": {"path": str(NB_DIR)}})
    client.execute()
    nbformat.write(nb, SAIDA)
    erros = [c for c in nb.cells if c.cell_type == "code"
             and any(o.get("output_type") == "error"
                     for o in c.get("outputs", []))]
    print(f"EXEC_OK — {sum(1 for c in nb.cells if c.cell_type=='code')} code, "
          f"{len(erros)} erros → {SAIDA.name}")


if __name__ == "__main__":
    main()
