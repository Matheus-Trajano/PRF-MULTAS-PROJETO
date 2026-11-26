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

MD_G2 = """\
---

## Gráfico 2 — Do ano ao dia: como as multas se distribuem no tempo?

**Pergunta:** mostrando os **anos do início ao fim** (2007–2025), como as
multas se distribuem em cada nível — **ano → mês → semana → dia** — e qual a
participação de cada período **dentro do seu período pai**?

**Resposta:** o total geral é **92.215.588** multas e o intervalo vai de
**1.855.460** (2007) a **10.204.474** (2025) — 2025 sozinho representa
**11,1%** de tudo. O mês mais crítico foi **dezembro/2024, com 1.059.685**
multas (**12,2%** daquele ano) e, dentro de cada mês, as **semanas 2 a 4
concentram 69,1%** de todas as autuações. **Métrica em % do período pai:** no
nível anos o denominador é o total geral; em cada nível seguinte, o total do
ano/mês/semana selecionado — por isso **cada nível soma 100%** do seu período.

**Interativo (HTML):** clique numa barra para descer (ano → mês → semana →
dia) e use o caminho no topo para voltar.
"""

CODE_G2_DATA = '''\
import calendar

ORDEM_MES = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARCO": 3, "ABRIL": 4, "MAIO": 5,
    "JUNHO": 6, "JULHO": 7, "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10,
    "NOVEMBRO": 11, "DEZEMBRO": 12,
}
NOMES_MES = {str(v): k for k, v in ORDEM_MES.items()}

anos_df = con.execute(
    f"SELECT ANO, COUNT(*) AS qtd FROM read_parquet('{BASE}') GROUP BY 1 ORDER BY 1"
).df()
meses_df = con.execute(
    f"SELECT ANO, MES, COUNT(*) AS qtd FROM read_parquet('{BASE}') GROUP BY 1, 2"
).df()
semanas_df = con.execute(
    f"SELECT ANO, MES, SEMANA_DO_MES AS sem, COUNT(*) AS qtd "
    f"FROM read_parquet('{BASE}') GROUP BY 1, 2, 3"
).df()
dias_df = con.execute(
    f"SELECT ANO, MES, SEMANA_DO_MES AS sem, DAY(DATA_INFRACAO) AS dia, "
    f"MAX(DIA_SEMANA) AS dia_semana, COUNT(*) AS qtd "
    f"FROM read_parquet('{BASE}') GROUP BY 1, 2, 3, 4"
).df()

meses_df["_m"] = meses_df["MES"].map(ORDEM_MES)
semanas_df["_m"] = semanas_df["MES"].map(ORDEM_MES)
dias_df["_m"] = dias_df["MES"].map(ORDEM_MES)
assert meses_df["_m"].notna().all() and semanas_df["sem"].notna().all()

DADOS = {"total": int(TOTAL), "anos": [], "meses": {}, "semanas": {}, "dias": {}}
for r in anos_df.to_dict("records"):
    DADOS["anos"].append({"k": str(int(r["ANO"])), "rot": str(int(r["ANO"])),
                          "qtd": int(r["qtd"])})
for r in meses_df.sort_values(["ANO", "_m"]).to_dict("records"):
    DADOS["meses"].setdefault(str(int(r["ANO"])), []).append(
        {"k": str(int(r["_m"])), "rot": r["MES"], "qtd": int(r["qtd"])})
for r in semanas_df.sort_values(["ANO", "_m", "sem"]).to_dict("records"):
    ultimo = calendar.monthrange(int(r["ANO"]), int(r["_m"]))[1]
    # SEMANA_DO_MES da base = round((dia - 1) / 7 + 1) → limites 1-4, 5-11,
    # 12-18, 19-25, 26-fim (confirmei: bate 31/31 pares distintos sem×dia)
    d1 = max(1, 7 * int(r["sem"]) - 9)
    d2 = min(7 * int(r["sem"]) - 3, ultimo)
    DADOS["semanas"].setdefault(f"{int(r['ANO'])}-{int(r['_m'])}", []).append(
        {"k": str(int(r["sem"])),
         "rot": f"Semana {int(r['sem'])} ({d1:02d}-{d2:02d})",
         "qtd": int(r["qtd"])})
for r in dias_df.sort_values(["ANO", "_m", "sem", "dia"]).to_dict("records"):
    chave = f"{int(r['ANO'])}-{int(r['_m'])}-{int(r['sem'])}"
    DADOS["dias"].setdefault(chave, []).append(
        {"k": str(int(r["dia"])),
         "rot": f"{int(r['dia']):02d} {chr(183)} {r['dia_semana']}",
         "qtd": int(r["qtd"])})

# ---- asserts: coerência de cada nível (soma do filho == total do pai) ----
assert [i["k"] for i in DADOS["anos"]] == [str(y) for y in range(2007, 2026)]
assert sum(i["qtd"] for i in DADOS["anos"]) == TOTAL_ESPERADO
n_meses = sum(len(v) for v in DADOS["meses"].values())
assert n_meses == 19 * 12 - 1, f"{n_meses} meses — junho/2024 não existe (227 esperado)"
for a in DADOS["anos"]:
    meses = DADOS["meses"][a["k"]]
    assert sum(i["qtd"] for i in meses) == a["qtd"], f"meses não fecham em {a['k']}"
    esperados = [str(m) for m in range(1, 13)
                 if not (a["k"] == "2024" and m == 6)]
    assert [i["k"] for i in meses] == esperados, f"ordem/meses errada em {a['k']}"
    for m in meses:
        semanas = DADOS["semanas"][f"{a['k']}-{m['k']}"]
        assert sum(i["qtd"] for i in semanas) == m["qtd"], \
            f"semanas não fecham em {a['k']}-{m['k']}"
        assert [i["k"] for i in semanas] == \
            [str(s) for s in range(1, len(semanas) + 1)]
        for w in semanas:
            dias = DADOS["dias"][f"{a['k']}-{m['k']}-{w['k']}"]
            assert sum(i["qtd"] for i in dias) == w["qtd"], \
                f"dias não fecham em {a['k']}-{m['k']}-S{w['k']}"
            for i in dias:
                # SEMANA_DO_MES da base = round((dia - 1) / 7 + 1):
                # sem 1 = dias 1-4, 2 = 5-11, 3 = 12-18, 4 = 19-25, 5 = 26-fim
                assert round((int(i["k"]) - 1) / 7 + 1) == int(w["k"]), \
                    f"dia {i['k']} fora da semana {w['k']} em {a['k']}-{m['k']}"

# ---- asserts: os números citados na Resposta ----
anos_map = {i["k"]: i["qtd"] for i in DADOS["anos"]}
assert anos_map["2007"] == 1_855_460 and anos_map["2025"] == 10_204_474
assert round(100 * anos_map["2025"] / TOTAL_ESPERADO, 1) == 11.1
t2024 = sum(i["qtd"] for i in DADOS["meses"]["2024"])
dez24 = next(i for i in DADOS["meses"]["2024"] if i["rot"] == "DEZEMBRO")
assert t2024 == 8_710_022 and dez24["qtd"] == 1_059_685
assert round(100 * dez24["qtd"] / t2024, 1) == 12.2
s234 = sum(i["qtd"] for meses in DADOS["semanas"].values()
           for i in meses if i["k"] in {"2", "3", "4"})
assert s234 == 63_686_578
assert round(100 * s234 / TOTAL_ESPERADO, 1) == 69.1

print(f"DADOS: {len(DADOS['anos'])} anos · {n_meses} meses · "
      f"{sum(len(v) for v in DADOS['semanas'].values())} semanas · "
      f"{sum(len(v) for v in DADOS['dias'].values())} dias · "
      f"total {br(TOTAL)} — todos os níveis fecham 100%")
'''

CODE_G2_HTML = '''\
import json
import re

MSG_G2 = "Do ano ao dia — clique para explorar as multas de 2007 a 2025"
LEG_G2_1 = ("Barras: % do período pai — anos sobre o total geral (92.215.588); "
            "meses sobre o ano; semanas sobre o mês; dias sobre a semana.")
LEG_G2_2 = ("Clique na barra para descer e no caminho do topo para voltar; "
            "cada nível soma 100% do seu período.")

# --- visão inicial (anos, início ao fim), no padrão titulo()/pct() ---
g2 = DADOS["anos"]
x2 = [i["rot"] for i in g2]
y2 = [100 * i["qtd"] / DADOS["total"] for i in g2]
rot2 = [f"{v:.2f}%".replace(".", ",") for v in y2]
fig2 = go.Figure(go.Bar(
    x=x2, y=y2,
    text=rot2, textposition="outside", textfont=dict(color="#922b21"),
    customdata=np.stack([[br(i["qtd"]) for i in g2], rot2], axis=-1),
    marker=dict(color=y2, colorscale=[[0, "#f5b7b1"], [1, "#922b21"]],
                colorbar=dict(title="%", thickness=12, len=0.5,
                              tickformat=".2f")),
    hovertemplate=("<b>%{x}</b><br>%{customdata[1]} do total geral<br>"
                   "Multas: %{customdata[0]}<extra></extra>"),
))
fig2.update_layout(
    title=titulo(MSG_G2, LEG_G2_1, LEG_G2_2),
    xaxis=dict(title="", categoryorder="array", categoryarray=x2,
               gridcolor="#e8e8e8"),
    yaxis=dict(title="% do período", ticksuffix="%", tickformat=".2f",
               gridcolor="#e8e8e8", rangemode="tozero",
               range=[0, max(y2) * 1.18]),
    plot_bgcolor="white", height=640, margin=dict(l=70, r=60, t=130, b=70),
)
assert len(x2) == 19 and x2 == [str(y) for y in range(2007, 2026)]
assert abs(y2[0] - 2.01) < 0.01 and abs(max(y2) - 11.07) < 0.01

# --- HTML interativo: gráfico + caminho (breadcrumb) + drill por clique ---
html_str = fig2.to_html(include_plotlyjs=True, full_html=True,
                        config={"displayModeBar": False})
assert "</body>" in html_str
if "charset" not in html_str:
    html_str = html_str.replace("<head>", "<head><meta charset=\\"utf-8\\">", 1)
div_id = re.search(r\'<div id="([^"]+)"\', html_str).group(1)

CSS = ("#g2_crumb{font:600 14px/26px \'Open Sans\',Helvetica,Arial,sans-serif;"
       "color:#922b21;margin:4px 2px 6px 2px;}"
       "#g2_crumb .gc{background:#fff;border:1px solid #c0392b;color:#922b21;"
       "border-radius:4px;padding:2px 10px;margin-right:2px;cursor:pointer;"
       "font:inherit;}"
       "#g2_crumb .gc:hover{background:#c0392b;color:#fff;}")

JS_TMPL = """(function () {
  const D = __DADOS__;
  const DIV = __DIV__;
  const MSG = __MSG__;
  const LEG1 = __LEG1__;
  const LEG2 = __LEG2__;
  const NOMES = __NOMES__;
  let path = [];

  function brInt(v) { return v.toLocaleString('pt-BR'); }
  function brPct(v) {
    return v.toLocaleString('pt-BR', {minimumFractionDigits: 2,
                                      maximumFractionDigits: 2}) + '%';
  }
  function soma(lista) {
    return lista.reduce(function (s, i) { return s + i.qtd; }, 0);
  }
  function totalAno(a) { return soma(D.meses[a]); }
  function totalMes(a, m) { return soma(D.semanas[a + '-' + m]); }
  function totalSem(a, m, s) { return soma(D.dias[a + '-' + m + '-' + s]); }
  function estado() {
    if (path.length === 0) {
      return {itens: D.anos, total: D.total, nivel: 0,
              rot: '2007-2025 · % do total geral'};
    }
    const a = path[0];
    if (path.length === 1) {
      return {itens: D.meses[a], total: totalAno(a), nivel: 1,
              rot: a + ' · % do total do ano'};
    }
    const m = path[1];
    if (path.length === 2) {
      return {itens: D.semanas[a + '-' + m], total: totalMes(a, m), nivel: 2,
              rot: NOMES[m] + '/' + a + ' · % do total do mês'};
    }
    const s = path[2];
    return {itens: D.dias[a + '-' + m + '-' + s], total: totalSem(a, m, s),
            nivel: 3,
            rot: 'Semana ' + s + ' de ' + NOMES[m] + '/' + a +
                 ' · % do total da semana'};
  }
  function dom(n) {
    return ['do total geral', 'do ano', 'do mês', 'da semana'][n];
  }
  function crumb(e) {
    const b = ['<button class="gc" data-p="0">Anos</button>'];
    if (path.length > 0) {
      b.push(' &#8250; <button class="gc" data-p="1">' + path[0] + '</button>');
    }
    if (path.length > 1) {
      b.push(' &#8250; <button class="gc" data-p="2">' + NOMES[path[1]] +
             '</button>');
    }
    if (path.length > 2) {
      b.push(' &#8250; <button class="gc" data-p="3">Semana ' + path[2] +
             '</button>');
    }
    if (path.length >= 3) { b.push(' &#8250; <b>Dias</b>'); }
    return b.join('') +
      '<span style="float:right;">' + e.rot + '</span>';
  }
  function render() {
    const e = estado();
    const y = e.itens.map(function (i) {
      return e.total ? 100 * i.qtd / e.total : 0;
    });
    const cd = e.itens.map(function (i, idx) {
      return [brInt(i.qtd), brPct(y[idx]), String(i.k)];
    });
    const trace = {
      type: 'bar',
      x: e.itens.map(function (i) { return i.rot; }),
      y: y,
      customdata: cd,
      text: y.map(brPct),
      textposition: 'outside',
      textfont: {color: '#922b21'},
      marker: {color: y, colorscale: [[0, '#f5b7b1'], [1, '#922b21']],
               colorbar: {title: '%', thickness: 12, len: 0.5,
                          tickformat: '.2f'}},
      hovertemplate: '<b>%{x}</b><br>%{customdata[1]} ' + dom(e.nivel) +
                     '<br>Multas: %{customdata[0]}<extra></extra>'
    };
    const layout = {
      title: {text: '<b>' + MSG + '</b><br><sup>' + LEG1 + '<br>' + LEG2 +
                    '</sup>',
              x: 0.01, xanchor: 'left', y: 0.95, yanchor: 'top',
              automargin: true, font: {size: 16, color: '#1a1a1a'}},
      xaxis: {categoryorder: 'array',
              categoryarray: e.itens.map(function (i) { return i.rot; }),
              gridcolor: '#e8e8e8'},
      yaxis: {title: '% do período', ticksuffix: '%', tickformat: '.2f',
              gridcolor: '#e8e8e8', rangemode: 'tozero',
              range: [0, Math.max.apply(null, y) * 1.18]},
      plot_bgcolor: 'white', height: 640,
      margin: {l: 70, r: 60, t: 130, b: 70}
    };
    Plotly.react(DIV, [trace], layout, {displayModeBar: false,
                                        responsive: true});
    document.getElementById('g2_crumb').innerHTML = crumb(e);
  }

  document.getElementById('g2_crumb').addEventListener('click',
    function (ev) {
      const b = ev.target.closest('button.gc');
      if (!b) { return; }
      path = path.slice(0, parseInt(b.getAttribute('data-p'), 10));
      render();
    });
  document.getElementById(DIV).on('plotly_click', function (ev) {
    const p = ev.points && ev.points[0];
    if (!p || !p.customdata) { return; }
    const k = String(p.customdata[2]);
    const e = estado();
    if (e.nivel === 0) { path = [k]; }
    else if (e.nivel === 1) { path = [path[0], k]; }
    else if (e.nivel === 2) { path = [path[0], path[1], k]; }
    else { return; }
    render();
  });
  render();
})();"""

JS = (JS_TMPL
      .replace("__DADOS__", json.dumps(DADOS, ensure_ascii=False))
      .replace("__DIV__", json.dumps(div_id))
      .replace("__MSG__", json.dumps(MSG_G2))
      .replace("__LEG1__", json.dumps(LEG_G2_1))
      .replace("__LEG2__", json.dumps(LEG_G2_2))
      .replace("__NOMES__", json.dumps(NOMES_MES)))

html_str = html_str.replace(
    f\'<div id="{div_id}"\',
    f"<style>{CSS}</style><div id=\\"g2_crumb\\"></div><div id=\\"{div_id}\\"",
    1,
)
html_str = html_str.replace("</body>", f"<script>{JS}</script></body>", 1)

out = DIR_RESULTADOS / "g2_drill_temporal.html"
out.write_text(html_str, encoding="utf-8")
try:
    fig2.write_image(DIR_RESULTADOS / "g2_drill_temporal.png",
                     width=1600, height=900, scale=2)
except Exception:
    print("PNG não gerado (kaleido precisa de Chrome instalado); HTML salvo.")

assert out.exists() and out.stat().st_size > 4_000_000, "HTML do g2 pequeno demais"
assert "plotly_click" in html_str and "g2_crumb" in html_str
from IPython.display import IFrame, display
print(f"resultados/: {out.name} ({out.stat().st_size:,} bytes)")
display(IFrame(src="../resultados/g2_drill_temporal.html",
               width="100%", height=760))
'''

MD_G3 = """\
---

## Gráfico 3 — Top 10 de tipos de veículo e as causas de cada um (por período)

**Pergunta:** quais são os 10 tipos de veículo com mais multas — e, ao
**selecionar um tipo em qualquer recorte temporal** (ano, mês, semana, dia),
quais são as **multas (causas) que mais ocorrem** com aquele tipo?

**Resposta:** **PASSAGEIRO lidera com 28.070.960 multas (30,4%)**, seguido de
**NAO INFORMADO (17.194.616 — 18,6%)** e **AUTOMOVEL (12.652.194 — 13,7%)**;
o top10 concentra **84.702.589 autuações (91,9%)**. O eixo é **híbrido**
(regra acordada): `TIPO_VEICULO` quando existe (**31,4%** — 2022–2025), senão
a `ESPECIE` original (**50,2%** — 2007–2021) e, na ausência dos dois,
**NAO INFORMADO** (**18,4%**). Ao clicar num tipo, as barras viram as
**top5 causas dele no período selecionado** — ex.: velocidade até 20% =
7.459.810 em AUTOMOVEL. **Métrica: % do período pai** — tipos sobre o total
do período; causas sobre o total do tipo (cada recorte soma 100% no seu
nível). **Menus Ano → Mês → Semana → Dia** fazem o recorte temporal.
"""

CODE_G3_DATA = '''\
import json
from collections import defaultdict

con.execute("SET temp_directory='/tmp/duck_spill'")

TIPO_EF = ("COALESCE(NULLIF(TRIM(TIPO_VEICULO), ''), NULLIF(TRIM(ESPECIE), ''), "
           "'NAO INFORMADO')")

# ---- 1) grão dia × tipo (uma varredura) e roll-up para todos os períodos ----
grao = con.execute(f"""
    SELECT ANO, MES, SEMANA_DO_MES AS sem, DAY(DATA_INFRACAO) AS dia,
           {TIPO_EF} AS tipo, COUNT(*) AS q
    FROM read_parquet('{BASE}')
    GROUP BY 1, 2, 3, 4, 5
""").df()

tot_periodo = defaultdict(int)
cont_tipo = defaultdict(lambda: defaultdict(int))
for a, m, s, d, t, q in zip(grao["ANO"], grao["MES"], grao["sem"],
                            grao["dia"], grao["tipo"], grao["q"]):
    a, m, s, d, q = int(a), ORDEM_MES[m], int(s), int(d), int(q)
    for p in ("", str(a), f"{a}-{m}", f"{a}-{m}-{s}", f"{a}-{m}-{s}-{d}"):
        tot_periodo[p] += q
        cont_tipo[p][t] += q
del grao

# por período, lista ordenada (tipo, qtd) — já agregada por tipo
por_periodo = {p: sorted(d.items(), key=lambda x: -x[1])
               for p, d in cont_tipo.items()}

# ---- 2) coerência total com o Gráfico 2 (DADOS) em todos os níveis ----
chaves_g2 = {""}
for a in DADOS["anos"]:
    chaves_g2.add(a["k"])
    for m in DADOS["meses"][a["k"]]:
        chaves_g2.add(f"{a['k']}-{m['k']}")
        for w in DADOS["semanas"][f"{a['k']}-{m['k']}"]:
            chaves_g2.add(f"{a['k']}-{m['k']}-{w['k']}")
            for dd in DADOS["dias"][f"{a['k']}-{m['k']}-{w['k']}"]:
                chaves_g2.add(f"{a['k']}-{m['k']}-{w['k']}-{dd['k']}")
assert set(tot_periodo) == chaves_g2, "períodos do g3 diferentes do g2"

def total_dados(p: str) -> int:
    if p == "":
        return DADOS["total"]
    partes = p.split("-")
    if len(partes) == 1:
        return next(i["qtd"] for i in DADOS["anos"] if i["k"] == partes[0])
    if len(partes) == 2:
        return next(i["qtd"] for i in DADOS["meses"][partes[0]]
                    if i["k"] == partes[1])
    if len(partes) == 2 + 1:
        return next(i["qtd"] for i in
                    DADOS["semanas"][f"{partes[0]}-{partes[1]}"]
                    if i["k"] == partes[2])
    return next(i["qtd"] for i in
                DADOS["dias"][f"{partes[0]}-{partes[1]}-{partes[2]}"]
                if i["k"] == partes[3])

for p, tot in tot_periodo.items():
    assert tot == total_dados(p), f"total divergente no período {p!r}"

# ---- 3) vocabulário de tipos + top10 geral (números da Resposta) ----
geral = sorted(por_periodo[""], key=lambda x: -x[1])
tipos_vocab = [t for t, _ in geral]
tipo_idx = {t: i for i, t in enumerate(tipos_vocab)}
assert len(tipos_vocab) == 38 and tipos_vocab[0] == "PASSAGEIRO"
top10_geral = geral[:10]
soma_top10 = sum(q for _, q in top10_geral)
assert soma_top10 == 84_702_589
assert round(100 * soma_top10 / TOTAL_ESPERADO, 1) == 91.9
assert dict(top10_geral)["PASSAGEIRO"] == 28_070_960
assert dict(top10_geral)["NAO INFORMADO"] == 17_194_616
assert dict(top10_geral)["AUTOMOVEL"] == 12_652_194

# cobertura do eixo híbrido (números da Resposta)
cov = con.execute(f"""
    SELECT
      SUM(CASE WHEN TIPO_VEICULO IS NOT NULL AND TRIM(TIPO_VEICULO) <> ''
               THEN 1 ELSE 0 END),
      SUM(CASE WHEN (TIPO_VEICULO IS NULL OR TRIM(TIPO_VEICULO) = '')
                    AND ESPECIE IS NOT NULL AND TRIM(ESPECIE) <> ''
               THEN 1 ELSE 0 END),
      SUM(CASE WHEN (TIPO_VEICULO IS NULL OR TRIM(TIPO_VEICULO) = '')
                    AND (ESPECIE IS NULL OR TRIM(ESPECIE) = '')
               THEN 1 ELSE 0 END)
    FROM read_parquet('{BASE}')
""").fetchone()
assert tuple(int(x) for x in cov) == (28_967_629, 46_320_085, 16_927_874)

top10_set = {p: {t for t, _ in sorted(lst, key=lambda x: -x[1])[:10]}
             for p, lst in por_periodo.items()}

# ---- 4) top5 causas por (período, tipo) — uma consulta por nível ----
def top_causas(nivel: str):
    """[(periodo, tipo, causa, qtd)] — top5 causas por (período, tipo)."""
    if nivel == "":
        sql = f"""
            SELECT {TIPO_EF} AS tipo, DESCRICAO_ABRVIADA AS causa,
                   COUNT(*) AS q
            FROM read_parquet('{BASE}') GROUP BY 1, 2
            QUALIFY ROW_NUMBER() OVER (PARTITION BY {TIPO_EF}
                                       ORDER BY COUNT(*) DESC) <= 5"""
        df = con.execute(sql).df()
        return [("", t, c, int(q)) for t, c, q in
                zip(df["tipo"], df["causa"], df["q"])]
    if nivel == "ano":
        sql = f"""
            SELECT ANO, {TIPO_EF} AS tipo, DESCRICAO_ABRVIADA AS causa,
                   COUNT(*) AS q
            FROM read_parquet('{BASE}') GROUP BY 1, 2, 3
            QUALIFY ROW_NUMBER() OVER (PARTITION BY ANO, {TIPO_EF}
                                       ORDER BY COUNT(*) DESC) <= 5"""
        df = con.execute(sql).df()
        return [(str(int(a)), t, c, int(q)) for a, t, c, q in
                zip(df["ANO"], df["tipo"], df["causa"], df["q"])]
    if nivel == "mes":
        sql = f"""
            SELECT ANO, MES, {TIPO_EF} AS tipo, DESCRICAO_ABRVIADA AS causa,
                   COUNT(*) AS q
            FROM read_parquet('{BASE}') GROUP BY 1, 2, 3, 4
            QUALIFY ROW_NUMBER() OVER (PARTITION BY ANO, MES, {TIPO_EF}
                                       ORDER BY COUNT(*) DESC) <= 5"""
        df = con.execute(sql).df()
        return [(f"{int(a)}-{ORDEM_MES[m]}", t, c, int(q))
                for a, m, t, c, q in zip(df["ANO"], df["MES"], df["tipo"],
                                         df["causa"], df["q"])]
    if nivel == "sem":
        sql = f"""
            SELECT ANO, MES, SEMANA_DO_MES AS sem, {TIPO_EF} AS tipo,
                   DESCRICAO_ABRVIADA AS causa, COUNT(*) AS q
            FROM read_parquet('{BASE}') GROUP BY 1, 2, 3, 4, 5
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY ANO, MES, SEMANA_DO_MES, {TIPO_EF}
                ORDER BY COUNT(*) DESC) <= 5"""
        df = con.execute(sql).df()
        return [(f"{int(a)}-{ORDEM_MES[m]}-{int(s)}", t, c, int(q))
                for a, m, s, t, c, q in zip(df["ANO"], df["MES"], df["sem"],
                                            df["tipo"], df["causa"], df["q"])]
    sql = f"""
        SELECT ANO, MES, SEMANA_DO_MES AS sem, DAY(DATA_INFRACAO) AS dia,
               {TIPO_EF} AS tipo, DESCRICAO_ABRVIADA AS causa, COUNT(*) AS q
        FROM read_parquet('{BASE}') GROUP BY 1, 2, 3, 4, 5, 6
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY ANO, MES, SEMANA_DO_MES, DAY(DATA_INFRACAO),
                        {TIPO_EF}
            ORDER BY COUNT(*) DESC) <= 5"""
    df = con.execute(sql).df()
    return [(f"{int(a)}-{ORDEM_MES[m]}-{int(s)}-{int(d)}", t, c, int(q))
            for a, m, s, d, t, c, q in
            zip(df["ANO"], df["MES"], df["sem"], df["dia"], df["tipo"],
                df["causa"], df["q"])]

causas_pt = defaultdict(list)
for nivel in ("", "ano", "mes", "sem", "dia"):
    linhas = top_causas(nivel)
    for p, t, c, q in linhas:
        if t in top10_set.get(p, ()):
            causas_pt[(p, t)].append((c, q))
    print(f"  causas nível {nivel or 'geral'}: {len(linhas):,} linhas")

faltantes = [(p, t) for p, ts in top10_set.items() for t in ts
             if (p, t) not in causas_pt]
assert not faltantes, f"tipos sem causas: {faltantes[:5]}"
for k in causas_pt:
    causas_pt[k].sort(key=lambda x: -x[1])
    causas_pt[k] = causas_pt[k][:5]

# ---- 5) monta o JSON final (vocabulário + períodos) ----
cvocab = sorted({c for arr in causas_pt.values() for c, _ in arr})
cidx = {c: i for i, c in enumerate(cvocab)}

p_json = {}
for p in sorted(tot_periodo):
    lst = sorted(por_periodo[p], key=lambda x: -x[1])[:10]
    tflat, cdict = [], {}
    for t, q in lst:
        ti = tipo_idx[t]
        tflat += [ti, int(q)]
        cdict[str(ti)] = [v for c, q2 in causas_pt.get((p, t), [])
                          for v in (cidx[c], int(q2))]
    p_json[p] = {"q": int(tot_periodo[p]), "t": tflat, "c": cdict}

G3 = {"tv": tipos_vocab, "cv": cvocab, "p": p_json}
g3_json = json.dumps(G3, ensure_ascii=False, separators=(",", ":"))

assert set(G3["p"]) == chaves_g2
assert G3["p"][""]["q"] == TOTAL_ESPERADO
assert len(G3["tv"]) == 38 and len(G3["cv"]) == len(set(G3["cv"]))
assert len(g3_json) < 30_000_000, f"JSON do g3 grande: {len(g3_json):,}"
print(f"G3: {len(G3['p'])} períodos · {len(G3['tv'])} tipos · "
      f"{len(G3['cv'])} causas · JSON {len(g3_json):,} chars")
'''

CODE_G3_HTML = '''\
import json
import re

MSG_G3 = "PASSAGEIRO lidera com 30% das multas — top10 de tipos × causas por período"
LEG_G3_1 = ("Barras: % do período — eixo híbrido TIPO_VEICULO (2022–2025) + "
            "ESPECIE (2007–2021); NAO INFORMADO sem dado (18,4%).")
LEG_G3_2 = ("Menus Ano→Mês→Semana→Dia recortam o período; clique no tipo "
            "abre as top5 causas dele naquele período · 92.215.588 multas.")

# --- visão inicial: top10 tipos de 2007–2025 (padrão titulo()/pct()) ---
flat0 = G3["p"][""]["t"]
pares0 = list(zip(flat0[0::2], flat0[1::2]))[:10]
disp0 = pares0[::-1]
nomes0 = [G3["tv"][i] for i, _ in disp0]
vals0 = [100 * q / G3["p"][""]["q"] for _, q in disp0]
fig3 = go.Figure(go.Bar(
    x=vals0, y=nomes0, orientation="h",
    text=[f"{v:.2f}%".replace(".", ",") for v in vals0],
    textposition="outside", textfont=dict(color="#922b21"),
    customdata=np.stack([nomes0,
                         [br(q) for _, q in disp0],
                         [f"{v:.2f}%".replace(".", ",") for v in vals0]],
                        axis=-1),
    marker=dict(color=vals0, colorscale=[[0, "#f5b7b1"], [1, "#922b21"]],
                colorbar=dict(title="%", thickness=12, len=0.5,
                              tickformat=".2f")),
    hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[2]} do período<br>"
                   "Multas: %{customdata[1]}<extra></extra>"),
))
fig3.update_layout(
    title=titulo(MSG_G3, LEG_G3_1, LEG_G3_2),
    xaxis=dict(title="% do período (2007–2025)", ticksuffix="%",
               tickformat=".2f", gridcolor="#e8e8e8", rangemode="tozero",
               range=[0, max(vals0) * 1.18]),
    yaxis=dict(title="", automargin=True),
    plot_bgcolor="white", height=660, margin=dict(l=210, r=70, t=130, b=60),
)
assert nomes0[-1] == "PASSAGEIRO" and abs(vals0[-1] - 30.44) < 0.01
assert len(nomes0) == 10
assert abs(sum(vals0) - 91.86) < 0.05

# --- HTML interativo: menus de período + clique no tipo → causas ---
html_str = fig3.to_html(include_plotlyjs=True, full_html=True,
                        config={"displayModeBar": False})
assert "</body>" in html_str
if "charset" not in html_str:
    html_str = html_str.replace("<head>", "<head><meta charset=\\"utf-8\\">", 1)
div_id = re.search(r\'<div id="([^"]+)"\', html_str).group(1)

MENUS = {
    "anos": [[i["k"], i["rot"]] for i in DADOS["anos"]],
    "meses": {a: [[i["k"], i["rot"]] for i in lst]
              for a, lst in DADOS["meses"].items()},
    "semanas": {k: [[i["k"], i["rot"]] for i in lst]
                for k, lst in DADOS["semanas"].items()},
    "dias": {k: [[i["k"], i["rot"]] for i in lst]
             for k, lst in DADOS["dias"].items()},
    "NOMES": NOMES_MES,
}

CSS = ("#g3_ui{font:600 14px/26px 'Open Sans',Helvetica,Arial,sans-serif;"
       "color:#922b21;margin:4px 2px 2px 2px;}"
       "#g3_menus label{margin-right:14px;}"
       "#g3_menus select{font:inherit;border:1px solid #c0392b;"
       "border-radius:4px;padding:2px 6px;color:#922b21;background:#fff;}"
       "#g3_info{float:right;color:#555;font-weight:600;}"
       "#g3_crumb{margin:6px 0 2px 0;min-height:26px;}"
       "#g3_crumb .gc{background:#fff;border:1px solid #c0392b;"
       "color:#922b21;border-radius:4px;padding:2px 10px;cursor:pointer;"
       "font:inherit;}"
       "#g3_crumb .gc:hover{background:#c0392b;color:#fff;}"
       ".g3-hint{color:#7f8c8d;font-weight:600;}")

JS_TMPL = """(function () {
  const G3 = __G3__;
  const D2 = __MENUS__;
  const DIV = __DIV__;
  const MSG = __MSG__;
  const LEG1 = __LEG1__;
  const LEG2 = __LEG2__;
  let per = {a: '', m: '', s: '', d: ''};
  let tipoSel = null;

  function brInt(v) { return v.toLocaleString('pt-BR'); }
  function brPct(v) {
    return v.toLocaleString('pt-BR', {minimumFractionDigits: 2,
                                      maximumFractionDigits: 2}) + '%';
  }
  function pk() {
    return [per.a, per.m, per.s, per.d].filter(Boolean).join('-');
  }
  function labelPeriodo() {
    const p = [];
    if (per.a) { p.push(per.a); }
    if (per.m) { p.push(D2.NOMES[per.m]); }
    if (per.s) {
      const ws = D2.semanas[per.a + '-' + per.m] || [];
      const w = ws.find(function (x) { return x[0] === per.s; });
      p.push(w ? w[1] : 'Semana ' + per.s);
    }
    if (per.d) {
      const ds = D2.dias[per.a + '-' + per.m + '-' + per.s] || [];
      const dd = ds.find(function (x) { return x[0] === per.d; });
      p.push(dd ? dd[1] : 'Dia ' + per.d);
    }
    return p.length ? p.join(' · ') : 'Todos os anos (2007–2025)';
  }
  function fill(sel, opts, ph) {
    while (sel.firstChild) { sel.removeChild(sel.firstChild); }
    const o0 = document.createElement('option');
    o0.value = ''; o0.textContent = ph;
    sel.appendChild(o0);
    opts.forEach(function (x) {
      const o = document.createElement('option');
      o.value = x[0]; o.textContent = x[1];
      sel.appendChild(o);
    });
    sel.disabled = opts.length === 0;
  }
  function tiposTop(P) {
    const out = [];
    for (let i = 0; i < P.t.length; i += 2) {
      out.push([P.t[i], P.t[i + 1]]);
    }
    return out;
  }
  function render() {
    const P = G3.p[pk()];
    let trace, info, crumb;
    if (tipoSel === null) {
      const top = tiposTop(P).slice(0, 10).reverse();
      const xv = top.map(function (x) { return 100 * x[1] / P.q; });
      const cd = top.map(function (x, i) {
        return [G3.tv[x[0]], brInt(x[1]), brPct(xv[i]), x[0]];
      });
      trace = {
        type: 'bar', orientation: 'h',
        x: xv,
        y: top.map(function (x) { return G3.tv[x[0]]; }),
        text: xv.map(brPct), textposition: 'outside',
        textfont: {color: '#922b21'},
        customdata: cd,
        marker: {color: xv, colorscale: [[0, '#f5b7b1'], [1, '#922b21']],
                 colorbar: {title: '%', thickness: 12, len: 0.5,
                            tickformat: '.2f'}},
        hovertemplate: '<b>%{customdata[0]}</b><br>%{customdata[2]} do período' +
                       '<br>Multas: %{customdata[1]}<extra></extra>'
      };
      const soma = top.reduce(function (s, x) { return s + x[1]; }, 0);
      info = brInt(P.q) + ' multas no período · top10 = ' + brInt(soma) +
             ' (' + brPct(100 * soma / P.q) + ')';
      crumb = '<span class="g3-hint">Clique numa barra para ver as ' +
              'multas (causas) daquele tipo</span>';
    } else {
      const hit = tiposTop(P).find(function (x) { return x[0] === tipoSel; });
      if (!hit) { tipoSel = null; render(); return; }
      const nomeTipo = G3.tv[tipoSel];
      const cf = (P.c && P.c[String(tipoSel)]) || [];
      const causas = [];
      for (let i = 0; i < cf.length; i += 2) {
        causas.push([cf[i], cf[i + 1]]);
      }
      causas.reverse();
      const xv = causas.map(function (x) { return 100 * x[1] / hit[1]; });
      const cd = causas.map(function (x, i) {
        return [G3.cv[x[0]], brInt(x[1]), brPct(xv[i])];
      });
      trace = {
        type: 'bar', orientation: 'h',
        x: xv,
        y: causas.map(function (x) { return G3.cv[x[0]]; }),
        text: xv.map(brPct), textposition: 'outside',
        textfont: {color: '#922b21'},
        customdata: cd,
        marker: {color: xv, colorscale: [[0, '#f5b7b1'], [1, '#922b21']],
                 colorbar: {title: '%', thickness: 12, len: 0.5,
                            tickformat: '.2f'}},
        hovertemplate: '<b>%{customdata[0]}</b><br>%{customdata[2]} do tipo' +
                       '<br>Multas: %{customdata[1]}<extra></extra>'
      };
      info = nomeTipo + ': ' + brInt(hit[1]) + ' multas (' +
             brPct(100 * hit[1] / P.q) + ' do período) · top5 causas = ' +
             brPct(xv.reduce(function (s, v) { return s + v; }, 0)) +
             ' do tipo';
      crumb = '<button class="gc" id="g3_back">‹ Voltar aos tipos</button>' +
              ' <b>' + nomeTipo + '</b> — causas em ' + labelPeriodo();
    }
    const layout = {
      title: {text: '<b>' + MSG + '</b><br><sup>' + LEG1 + '<br>' + LEG2 +
                    '</sup>',
              x: 0.01, xanchor: 'left', y: 0.95, yanchor: 'top',
              automargin: true, font: {size: 16, color: '#1a1a1a'}},
      xaxis: {title: tipoSel === null ? '% do período' : '% do total do tipo',
              ticksuffix: '%', tickformat: '.2f', gridcolor: '#e8e8e8',
              rangemode: 'tozero',
              range: [0, Math.max.apply(null, trace.x.concat([0.0001])) *
                        1.18]},
      yaxis: {title: '', automargin: true, categoryorder: 'array',
              categoryarray: trace.y.slice()},
      plot_bgcolor: 'white', height: 660,
      margin: {l: 210, r: 70, t: 130, b: 60}
    };
    Plotly.react(DIV, [trace], layout,
                 {displayModeBar: false, responsive: true});
    document.getElementById('g3_info').textContent = info;
    document.getElementById('g3_crumb').innerHTML = crumb;
    const back = document.getElementById('g3_back');
    if (back) {
      back.addEventListener('click', function () {
        tipoSel = null;
        render();
      });
    }
  }

  const ui = document.getElementById('g3_ui');
  ui.innerHTML =
    '<div id="g3_menus">' +
    '<label>Ano <select id="g3_ano"></select></label>' +
    '<label>Mês <select id="g3_mes" disabled></select></label>' +
    '<label>Semana <select id="g3_sem" disabled></select></label>' +
    '<label>Dia <select id="g3_dia" disabled></select></label>' +
    '<span id="g3_info"></span></div>' +
    '<div id="g3_crumb"></div>';
  const selAno = document.getElementById('g3_ano');
  const selMes = document.getElementById('g3_mes');
  const selSem = document.getElementById('g3_sem');
  const selDia = document.getElementById('g3_dia');
  fill(selAno, D2.anos, 'Todos os anos');
  selAno.addEventListener('change', function () {
    per = {a: selAno.value, m: '', s: '', d: ''};
    fill(selMes, per.a ? (D2.meses[per.a] || []) : [], 'Todos os meses');
    fill(selSem, [], 'Todas');
    fill(selDia, [], 'Todos');
    render();
  });
  selMes.addEventListener('change', function () {
    per.m = selMes.value; per.s = ''; per.d = '';
    fill(selSem, (D2.semanas[per.a + '-' + per.m] || []), 'Todas');
    fill(selDia, [], 'Todos');
    render();
  });
  selSem.addEventListener('change', function () {
    per.s = selSem.value; per.d = '';
    fill(selDia, (D2.dias[per.a + '-' + per.m + '-' + per.s] || []),
         'Todos');
    render();
  });
  selDia.addEventListener('change', function () {
    per.d = selDia.value;
    render();
  });
  document.getElementById(DIV).on('plotly_click', function (ev) {
    const p = ev.points && ev.points[0];
    if (!p || !p.customdata) { return; }
    if (tipoSel === null && p.customdata.length >= 4) {
      tipoSel = p.customdata[3];
      render();
    }
  });
  render();
})();"""

JS = (JS_TMPL
      .replace("__G3__", g3_json)
      .replace("__MENUS__", json.dumps(MENUS, ensure_ascii=False,
                                       separators=(",", ":")))
      .replace("__DIV__", json.dumps(div_id))
      .replace("__MSG__", json.dumps(MSG_G3))
      .replace("__LEG1__", json.dumps(LEG_G3_1))
      .replace("__LEG2__", json.dumps(LEG_G3_2)))

html_str = html_str.replace(
    f\'<div id="{div_id}"\',
    f\'<style>{CSS}</style><div id="g3_ui"></div><div id="{div_id}">\',
    1,
)
html_str = html_str.replace("</body>", f"<script>{JS}</script></body>", 1)

out = DIR_RESULTADOS / "g3_top10_veiculos.html"
out.write_text(html_str, encoding="utf-8")
try:
    fig3.write_image(DIR_RESULTADOS / "g3_top10_veiculos.png",
                     width=1600, height=900, scale=2)
except Exception:
    print("PNG não gerado (kaleido precisa de Chrome instalado); HTML salvo.")

assert out.exists() and out.stat().st_size < 40_000_000, "HTML do g3 fora do limite"
for marca in ("plotly_click", "g3_ui", "g3_ano", "g3_back", "Plotly.react"):
    assert marca in html_str, f"HTML sem {marca}"
from IPython.display import IFrame, display
print(f"resultados/: {out.name} ({out.stat().st_size:,} bytes)")
display(IFrame(src="../resultados/g3_top10_veiculos.html",
               width="100%", height=780))
'''

MD_FECHO = """\
## Fechamento da Parte 6

| Gráfico | Pergunta que responde | Mensagem principal | Arquivo |
|---|---|---|---|
| 1 | Quais são as 10 causas de multa que mais ocorrem? | Velocidade = 52% das multas; top10 concentra 71,7% | `resultados/g1_top10_multas.html` |
| 2 | Como as multas se distribuem do ano ao dia? | % do período pai; drill ano→mês→semana→dia por clique | `resultados/g2_drill_temporal.html` |
| 3 | Quais são os top10 tipos de veículo e as causas de cada um em qualquer período? | PASSAGEIRO = 30,4%; top10 = 91,9%; clique no tipo → top5 causas do período | `resultados/g3_top10_veiculos.html` |

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
        nbformat.v4.new_markdown_cell(MD_G2),
        nbformat.v4.new_code_cell(CODE_G2_DATA),
        nbformat.v4.new_code_cell(CODE_G2_HTML),
        nbformat.v4.new_markdown_cell(MD_G3),
        nbformat.v4.new_code_cell(CODE_G3_DATA),
        nbformat.v4.new_code_cell(CODE_G3_HTML),
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
