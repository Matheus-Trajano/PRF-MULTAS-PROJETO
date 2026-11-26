#!/usr/bin/env python3
"""_build_eda.py — monta e EXECUTA notebooks/05_eda_plotly.ipynb (Etapa E).

Uso:  .venv/bin/python notebooks/_build_eda.py
Gera o ipynb com nbformat e executa com nbclient (0 erros = aprovado).
Fonte unica de dados: dados_tratados/agregados/*.parquet (12 arquivos).
"""
from __future__ import annotations

from pathlib import Path

import nbformat
from nbclient import NotebookClient

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "notebooks" / "05_eda_plotly.ipynb"

# ----------------------------------------------------------------------------
# CELULAS
# ----------------------------------------------------------------------------
MD_INTRO = """\
# EDA Plotly — Fase 3, Etapa E

Dashboard interativo de **multas da PRF (2007–2025)** com drill-down
ano → mês → semana → dia, conforme `docs/catalogo_graficos.md` (Etapa C) e
`docs/especificacao_interacoes.md` (Etapa D).

**Fonte única:** `dados_tratados/agregados/*.parquet` (13 tabelas leves).
Os 92.215.588 registros da base analítica **nunca** são carregados aqui —
todos os gráficos somam a coluna `qtd` dos agregados.

**Filtros globais** (topo): `ANO` e `UF` valem para TODOS os gráficos
(todos os agregados carregam `ANO` + `UF_INFRACAO`). O filtro `MUNICIPIO`
é explorado pelo drill do treemap geográfico (UF → município).

**Validação de aceite:** `soma(qtd) == 92.215.588` em todos os 13 agregados
(assert na última célula).

> **Nota de dado:** junho/2024 não consta na fonte original da PRF — o
> calendário 2024 salta de maio para julho. Não é falha de pipeline.
"""

C_SETUP = """\
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output

RAIZ = Path.cwd().resolve()
if not (RAIZ / "dados_tratados").exists():
    RAIZ = RAIZ.parent
AGG = RAIZ / "dados_tratados" / "agregados"
TOTAL_ESPERADO = 92_215_588

ORDEM_MES = ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO",
             "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
ORDEM_DIA = ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA", "SABADO", "DOMINGO"]
ORDEM_TURNO = ["MADRUGADA", "MANHA", "TARDE", "NOITE"]
ORDEM_FAIXA = ["00-40", "41-60", "61-80", "81-100", "101-120", "120+", "NAO_INFORMADO"]

px.defaults.template = "plotly_white"
con = duckdb.connect(":memory:")
con.execute("SET threads=4")


def ler(nome: str) -> pd.DataFrame:
    return con.execute(
        f"SELECT * FROM read_parquet('{AGG / (nome + '.parquet')}')"
    ).df()


NOMES = ["tempo_diario", "hora_diaria", "top_infracao", "top_br", "top_uf",
         "top_municipio", "origem_ocorrencia", "natureza", "veiculo_especie",
         "veiculo_marca", "abordagem", "velocidade_faixa", "km_faixa"]
D = {n: ler(n) for n in NOMES}

for _n, _df in D.items():
    _s = int(_df["qtd"].sum())
    assert _s == TOTAL_ESPERADO, f"{_n}: soma(qtd)={_s} != {TOTAL_ESPERADO}"
print(f"✓ {len(NOMES)} agregados carregados — soma(qtd) = {TOTAL_ESPERADO:,} em todos")
print("linhas: " + " | ".join(f"{n}={len(D[n]):,}" for n in NOMES))
"""

C_FILTROS = """\
ANOS = ["Todos"] + sorted(int(a) for a in D["top_uf"]["ANO"].unique())
UFS = ["Todos"] + sorted(D["top_uf"]["UF_INFRACAO"].dropna().unique().tolist())

_ESTILO = {"description_width": "45px"}
w_ano = widgets.Dropdown(options=ANOS, value="Todos", description="ANO:", style=_ESTILO)
w_uf = widgets.Dropdown(options=UFS, value="Todos", description="UF:", style=_ESTILO)
lbl_ano = widgets.HTML()
lbl_uf = widgets.HTML()


def aplicar(df: pd.DataFrame) -> pd.DataFrame:
    \"\"\"Aplica os filtros globais ANO/UF (colunas existem em todos os agregados).\"\"\"
    out = df
    if w_ano.value != "Todos" and "ANO" in out.columns:
        out = out[out["ANO"] == w_ano.value]
    if w_uf.value != "Todos" and "UF_INFRACAO" in out.columns:
        out = out[out["UF_INFRACAO"] == w_uf.value]
    return out


def _fmt(n) -> str:
    return f"{int(n):,}".replace(",", ".")


display(widgets.HBox([w_ano, w_uf]))
print("Filtros globais acima → atualizam KPIs e TODAS as seções abaixo.")
"""

C_KPI = """\
out_kpi = widgets.Output()


def desenhar_kpis(_=None):
    with out_kpi:
        clear_output(wait=True)
        t = aplicar(D["tempo_diario"])
        total = int(t["qtd"].sum())
        dias = t["DATA_INFRACAO"].nunique()
        media = total / dias if dias else 0
        pico = t.groupby("DATA_INFRACAO")["qtd"].sum().idxmax() if total else "-"
        pico_v = int(t.groupby("DATA_INFRACAO")["qtd"].sum().max()) if total else 0
        fimsemana = int(t.loc[t["FIM_DE_SEMANA"] == "SIM", "qtd"].sum())
        share_fs = 100 * fimsemana / total if total else 0
        ufs = aplicar(D["top_uf"])["UF_INFRACAO"].nunique()
        cards = [
            ("Multas (filtro atual)", _fmt(total)),
            ("Dias com dados", _fmt(dias)),
            ("Média/dia", _fmt(round(media))),
            ("Pico (dia)", f"{pico} · {_fmt(pico_v)}"),
            ("Fim de semana", f"{share_fs:.1f}%"),
            ("UFs no filtro", _fmt(ufs)),
        ]
        html = "<div style='display:flex;gap:10px;flex-wrap:wrap'>" + "".join(
            f"<div style='border:1px solid #ddd;border-radius:8px;"
            f"padding:8px 14px;background:#f8f9fa'>"
            f"<div style='font-size:11px;color:#666'>{k}</div>"
            f"<div style='font-size:18px;font-weight:600'>{v}</div></div>"
            for k, v in cards
        ) + "</div>"
        display(HTML(html))


w_ano.observe(desenhar_kpis, names="value")
w_uf.observe(desenhar_kpis, names="value")
display(out_kpi)
desenhar_kpis()
"""

C_TEMPORAL = """\
out_t = widgets.Output()

dd_mes = widgets.Dropdown(options=["Todos"] + ORDEM_MES, value="Todos",
                          description="Mês:", style={"description_width": "45px"})
dd_sem = widgets.Dropdown(options=["Todos"], value="Todos", description="Semana:",
                          style={"description_width": "45px"}, disabled=True)


def _rebuild_semanas(*_):
    t = aplicar(D["tempo_diario"])
    if w_ano.value == "Todos" or dd_mes.value == "Todos":
        dd_sem.options = ["Todos"]
        dd_sem.value = "Todos"
        dd_sem.disabled = True
        return
    t = t[t["MES"] == dd_mes.value]
    semanas = sorted(int(s) for s in t["SEMANA_DO_MES"].dropna().unique())
    dd_sem.options = ["Todos"] + semanas
    if dd_sem.value not in dd_sem.options:
        dd_sem.value = "Todos"
    dd_sem.disabled = False


def desenhar_temporal(_=None):
    with out_t:
        clear_output(wait=True)
        display(HTML("<h3>⏱ Temporal</h3>"))

        # --- (1) cascata ano → mês → semana → dia -------------------------
        t = aplicar(D["tempo_diario"])
        if w_ano.value == "Todos":
            g = (t.groupby("ANO", as_index=False)["qtd"].sum()
                   .sort_values("ANO"))
            fig = px.bar(g, x="ANO", y="qtd", title="Multas por ano",
                         labels={"qtd": "Multas", "ANO": "Ano"})
            trilha = "Todos os anos"
        elif dd_mes.value == "Todos":
            g = (t.groupby("MES", as_index=False)["qtd"].sum()
                   .assign(MES=lambda d: pd.Categorical(d["MES"], ORDEM_MES, ordered=True))
                   .sort_values("MES"))
            fig = px.bar(g, x="MES", y="qtd",
                         title=f"Multas por mês — {w_ano.value}",
                         labels={"qtd": "Multas", "MES": "Mês"})
            trilha = f"Todos › <b>{w_ano.value}</b> › todos os meses"
        elif dd_sem.value == "Todos":
            g = (t[t["MES"] == dd_mes.value]
                   .groupby("SEMANA_DO_MES", as_index=False)["qtd"].sum()
                   .sort_values("SEMANA_DO_MES"))
            fig = px.bar(g, x="SEMANA_DO_MES", y="qtd",
                         title=f"Multas por semana do mês — {w_ano.value} · {dd_mes.value}",
                         labels={"qtd": "Multas", "SEMANA_DO_MES": "Semana do mês"})
            trilha = (f"Todos › <b>{w_ano.value}</b> › <b>{dd_mes.value}</b> "
                      f"› todas as semanas")
        else:
            g = (t[(t["MES"] == dd_mes.value) & (t["SEMANA_DO_MES"] == dd_sem.value)]
                   .groupby("DATA_INFRACAO", as_index=False)["qtd"].sum()
                   .sort_values("DATA_INFRACAO"))
            fig = px.bar(g, x="DATA_INFRACAO", y="qtd",
                         title=(f"Multas por dia — {w_ano.value} · {dd_mes.value} "
                                f"· semana {dd_sem.value}"),
                         labels={"qtd": "Multas", "DATA_INFRACAO": "Data"})
            trilha = (f"Todos › <b>{w_ano.value}</b> › <b>{dd_mes.value}</b> › "
                      f"<b>semana {dd_sem.value}</b> › dias")
        fig.update_layout(height=340, margin=dict(t=50, b=40))
        display(HTML(f"📍 <b>Cascata:</b> {trilha} &nbsp; "
                     f"<span style='color:#888'>(use Mês/Semana para descer)</span>"))
        display(widgets.HBox([dd_mes, dd_sem]))
        display(fig)

        # --- (2) heatmap ano × mês ---------------------------------------
        piv = (t.pivot_table(index="ANO", columns="MES", values="qtd",
                             aggfunc="sum", fill_value=0)
                 .reindex(columns=ORDEM_MES, fill_value=0))
        fig2 = px.imshow(
            piv.values, x=ORDEM_MES, y=[str(a) for a in piv.index],
            labels=dict(x="Mês", y="Ano", color="Multas"),
            title="Multas por ano × mês (colorido = volume)",
            color_continuous_scale="Blues", aspect="auto",
            text_auto=".2s",
        )
        fig2.update_layout(height=380, margin=dict(t=50, b=40))
        display(fig2)

        # --- (3) dia da semana -------------------------------------------
        g3 = (t.groupby(["DIA_SEMANA_NUM", "DIA_SEMANA"], as_index=False)["qtd"].sum()
                .sort_values("DIA_SEMANA_NUM"))
        fig3 = px.bar(g3, x="DIA_SEMANA", y="qtd",
                      title="Multas por dia da semana",
                      labels={"qtd": "Multas", "DIA_SEMANA": "Dia"},
                      category_orders={"DIA_SEMANA": ORDEM_DIA})
        fig3.update_layout(height=300, margin=dict(t=50, b=40))
        display(fig3)

        # --- (4) fim de semana -------------------------------------------
        g4 = t.groupby("FIM_DE_SEMANA")["qtd"].sum().reset_index()
        fig4 = px.pie(g4, names="FIM_DE_SEMANA", values="qtd",
                      title="Fim de semana × dias úteis",
                      color_discrete_map={"SIM": "#ff7f0e", "NAO": "#1f77b4"})
        fig4.update_layout(height=300, margin=dict(t=50, b=40), legend_title_text="")
        display(fig4)

        # --- (5) hora do dia ---------------------------------------------
        h = aplicar(D["hora_diaria"]).groupby("HORA", as_index=False)["qtd"].sum()
        fig5 = px.line(h, x="HORA", y="qtd", markers=True,
                       title="Multas por hora do dia",
                       labels={"qtd": "Multas", "HORA": "Hora"})
        fig5.update_layout(height=300, margin=dict(t=50, b=40),
                           xaxis=dict(dtick=1, range=[-0.5, 23.5]))
        display(fig5)

        # --- (6) turno ----------------------------------------------------
        g6 = (aplicar(D["hora_diaria"]).groupby("TURNO", as_index=False)["qtd"].sum()
                .assign(TURNO=lambda d: pd.Categorical(d["TURNO"], ORDEM_TURNO, ordered=True))
                .sort_values("TURNO"))
        fig6 = px.bar(g6, x="TURNO", y="qtd", title="Multas por turno",
                      labels={"qtd": "Multas", "TURNO": "Turno"},
                      color="TURNO", color_discrete_sequence=px.colors.qualitative.Set2)
        fig6.update_layout(height=300, margin=dict(t=50, b=40), showlegend=False)
        display(fig6)


w_ano.observe(_rebuild_semanas, names="value")
dd_mes.observe(_rebuild_semanas, names="value")
w_ano.observe(desenhar_temporal, names="value")
w_uf.observe(desenhar_temporal, names="value")
dd_mes.observe(desenhar_temporal, names="value")
dd_sem.observe(desenhar_temporal, names="value")
display(out_t)
_rebuild_semanas()
desenhar_temporal()
"""

C_GEO = """\
out_g = widgets.Output()


def desenhar_geo(_=None):
    with out_g:
        clear_output(wait=True)
        display(HTML("<h3>🗺 Geográfica</h3>"))

        # (1) top 10 municípios
        m = (aplicar(D["top_municipio"])
               .groupby(["UF_INFRACAO", "NOM_MUNICIPIO"], as_index=False)["qtd"].sum())
        m["NOM_MUNICIPIO"] = m["NOM_MUNICIPIO"].fillna("NÃO INFORMADO")
        m["rot"] = m["NOM_MUNICIPIO"] + " (" + m["UF_INFRACAO"].fillna("??") + ")"
        top10 = m.nlargest(10, "qtd").sort_values("qtd")
        fig1 = px.bar(top10, x="qtd", y="rot", orientation="h",
                      title="Top 10 municípios (filtro atual)",
                      labels={"qtd": "Multas", "rot": "Município (UF)"})
        fig1.update_layout(height=360, margin=dict(t=50, b=40))
        display(fig1)

        # (2) ranking de UFs
        u = aplicar(D["top_uf"]).groupby("UF_INFRACAO", as_index=False)["qtd"].sum()
        u = u.sort_values("qtd", ascending=False)
        fig2 = px.bar(u, x="UF_INFRACAO", y="qtd", title="Multas por UF de infração",
                      labels={"qtd": "Multas", "UF_INFRACAO": "UF"})
        fig2.update_layout(height=320, margin=dict(t=50, b=40))
        display(fig2)

        # (3) matriz placa × localidade da infração
        o = aplicar(D["origem_ocorrencia"]).copy()
        o["UF_PLACA"] = o["UF_PLACA"].fillna("NÃO INFORMADO")
        o["UF_INFRACAO"] = o["UF_INFRACAO"].fillna("NÃO INFORMADO")
        mat = o.pivot_table(index="UF_PLACA", columns="UF_INFRACAO",
                            values="qtd", aggfunc="sum", fill_value=0)
        fig3 = px.imshow(np.log1p(mat.values),
                         x=list(mat.columns), y=list(mat.index),
                         labels=dict(x="UF da infração", y="UF da placa",
                                     color="log(1+multas)"),
                         title="Origem × ocorrência: UF da placa × UF da infração",
                         color_continuous_scale="Viridis", aspect="auto")
        fig3.update_layout(height=520, margin=dict(t=50, b=40))
        display(fig3)

        # (4) treemap UF → município (drill geográfico)
        tre = m[m["NOM_MUNICIPIO"] != "NÃO INFORMADO"].nlargest(300, "qtd")
        fig4 = px.treemap(tre, path=["UF_INFRACAO", "NOM_MUNICIPIO"], values="qtd",
                          title="Drill UF → município (top 300; clique p/ detalhar)",
                          color="qtd", color_continuous_scale="Blues")
        fig4.update_layout(height=440, margin=dict(t=50, b=40))
        display(fig4)

        # (5) top BRs
        b = (aplicar(D["top_br"]).groupby(["NUM_BR_INFRACAO", "BR_FORMATADA"],
                                           as_index=False)["qtd"].sum())
        b["rot"] = b["BR_FORMATADA"].fillna("SEM BR")
        top_br = b.nlargest(10, "qtd").sort_values("qtd")
        fig5 = px.bar(top_br, x="qtd", y="rot", orientation="h",
                      title="Top 10 BRs",
                      labels={"qtd": "Multas", "rot": "BR"})
        fig5.update_layout(height=320, margin=dict(t=50, b=40))
        display(fig5)

        # (6) histograma de KM (faixas de 50)
        k = aplicar(D["km_faixa"]).groupby("FAIXA_KM", as_index=False)["qtd"].sum()
        k = k.sort_values("FAIXA_KM")   # ordem lexicografica = ordem das faixas
        fig6 = px.bar(k, x="FAIXA_KM", y="qtd",
                      title="Distribuição por faixa de KM da infração",
                      labels={"qtd": "Multas", "FAIXA_KM": "Faixa de KM"})
        fig6.update_layout(height=340, margin=dict(t=50, b=40))
        display(fig6)

        # (7) KM por BR: top 12 BRs × faixa (heatmap log1p)
        kb = aplicar(D["km_faixa"]).copy()
        kb["rot"] = kb["BR_FORMATADA"].fillna("SEM BR")
        top12_br = kb.groupby("rot")["qtd"].sum().nlargest(12).index.tolist()
        kb = kb[kb["rot"].isin(top12_br)]
        matk = kb.pivot_table(index="rot", columns="FAIXA_KM", values="qtd",
                              aggfunc="sum", fill_value=0)
        matk = matk.reindex(sorted(matk.columns), axis=1)
        fig7 = px.imshow(np.log1p(matk.values), x=list(matk.columns),
                         y=list(matk.index),
                         labels=dict(x="Faixa de KM", y="BR", color="log(1+multas)"),
                         title="KM por BR — top 12 BRs (heatmap)",
                         color_continuous_scale="Greens", aspect="auto")
        fig7.update_layout(height=420, margin=dict(t=50, b=40))
        display(fig7)


w_ano.observe(desenhar_geo, names="value")
w_uf.observe(desenhar_geo, names="value")
display(out_g)
desenhar_geo()
"""

C_INFRACAO = """\
out_i = widgets.Output()


def desenhar_infracao(_=None):
    with out_i:
        clear_output(wait=True)
        display(HTML("<h3>🚨 Infração</h3>"))

        # (1) top 10 descrições
        d = (aplicar(D["top_infracao"]).groupby("DESCRICAO_ABRVIADA",
                                                 as_index=False)["qtd"].sum())
        top = d.nlargest(10, "qtd").sort_values("qtd")
        fig1 = px.bar(top, x="qtd", y="DESCRICAO_ABRVIADA", orientation="h",
                      title="Top 10 infrações mais autuadas",
                      labels={"qtd": "Multas", "DESCRICAO_ABRVIADA": "Descrição"})
        fig1.update_layout(height=380, margin=dict(t=50, b=40))
        display(fig1)

        # (2) natureza (heurística v1)
        n = (aplicar(D["natureza"]).groupby("NATUREZA_INFRA", as_index=False)["qtd"].sum()
               .sort_values("qtd", ascending=False))
        fig2 = px.bar(n, x="NATUREZA_INFRA", y="qtd",
                      title="Multas por natureza da infração",
                      labels={"qtd": "Multas", "NATUREZA_INFRA": "Natureza"},
                      color="NATUREZA_INFRA", color_discrete_sequence=px.colors.qualitative.Set2)
        fig2.update_layout(height=320, margin=dict(t=50, b=40), showlegend=False)
        display(fig2)

        # (3) faixa de velocidade medida
        v = (aplicar(D["velocidade_faixa"]).groupby("FAIXA_VELOCIDADE", as_index=False)["qtd"].sum()
               .assign(FAIXA=lambda d: pd.Categorical(d["FAIXA_VELOCIDADE"], ORDEM_FAIXA, ordered=True))
               .sort_values("FAIXA"))
        fig3 = px.bar(v, x="FAIXA_VELOCIDADE", y="qtd",
                      title="Multas por faixa de velocidade medida",
                      labels={"qtd": "Multas", "FAIXA_VELOCIDADE": "Faixa (km/h)"})
        fig3.update_layout(height=320, margin=dict(t=50, b=40))
        display(fig3)
        display(HTML("<span style='color:#888;font-size:12px'>"
                     "NAO_INFORMADO ≈ 68% (med_realizada ausente na fonte) — "
                     "esperado, não é falha do pipeline.</span>"))

        # (4) treemap enquadramento → descrição
        e = (aplicar(D["top_infracao"])
               .groupby(["ENQUADRAMENTO", "DESCRICAO_ABRVIADA"], as_index=False)["qtd"].sum()
               .nlargest(150, "qtd"))
        e["ENQUADRAMENTO"] = e["ENQUADRAMENTO"].fillna("SEM ENQUADRAMENTO")
        fig4 = px.treemap(e, path=["ENQUADRAMENTO", "DESCRICAO_ABRVIADA"], values="qtd",
                          title="Drill enquadramento → descrição (top 150)",
                          color="qtd", color_continuous_scale="Reds")
        fig4.update_layout(height=440, margin=dict(t=50, b=40))
        display(fig4)

        # (5) abordagem × assinatura
        a = (aplicar(D["abordagem"])
               .groupby(["TIP_ABORDAGEM", "IND_ASSINOU_AUTO"], as_index=False)["qtd"].sum())
        a["TIP_ABORDAGEM"] = a["TIP_ABORDAGEM"].fillna("NÃO INFORMADO")
        a["IND_ASSINOU_AUTO"] = a["IND_ASSINOU_AUTO"].fillna("NÃO INFORMADO")
        fig5 = px.bar(a, x="TIP_ABORDAGEM", y="qtd", color="IND_ASSINOU_AUTO",
                      title="Tipo de abordagem × assinatura do auto",
                      labels={"qtd": "Multas", "IND_ASSINOU_AUTO": "Assinou"})
        fig5.update_layout(height=320, margin=dict(t=50, b=40))
        display(fig5)


w_ano.observe(desenhar_infracao, names="value")
w_uf.observe(desenhar_infracao, names="value")
display(out_i)
desenhar_infracao()
"""

C_VEICULO = """\
out_v = widgets.Output()


def desenhar_veiculo(_=None):
    with out_v:
        clear_output(wait=True)
        display(HTML("<h3>🚗 Veículo</h3>"))

        ve = aplicar(D["veiculo_especie"]).copy()
        ve["ESPECIE"] = ve["ESPECIE"].fillna("NÃO INFORMADO")
        ve["TIPO_VEICULO"] = ve["TIPO_VEICULO"].fillna("NÃO INFORMADO")

        # (1) espécie (barras)
        e = ve.groupby("ESPECIE", as_index=False)["qtd"].sum().sort_values("qtd", ascending=False)
        fig1 = px.bar(e, x="ESPECIE", y="qtd", title="Multas por espécie de veículo",
                      labels={"qtd": "Multas", "ESPECIE": "Espécie"})
        fig1.update_layout(height=320, margin=dict(t=50, b=40))
        display(fig1)

        # (2) tipo de veículo (top 12)
        tv = (ve.groupby("TIPO_VEICULO", as_index=False)["qtd"].sum()
                .nlargest(12, "qtd").sort_values("qtd"))
        fig2 = px.bar(tv, x="qtd", y="TIPO_VEICULO", orientation="h",
                      title="Top 12 tipos de veículo",
                      labels={"qtd": "Multas", "TIPO_VEICULO": "Tipo"})
        fig2.update_layout(height=380, margin=dict(t=50, b=40))
        display(fig2)

        # (3) espécie × tipo (empilhado)
        st = (ve.groupby(["ESPECIE", "TIPO_VEICULO"], as_index=False)["qtd"].sum())
        top_tipos = st.groupby("TIPO_VEICULO")["qtd"].sum().nlargest(6).index
        st = st[st["TIPO_VEICULO"].isin(top_tipos)]
        st = st[st["ESPECIE"].isin(
            st.groupby("ESPECIE")["qtd"].sum().nlargest(6).index)]
        fig3 = px.bar(st, x="ESPECIE", y="qtd", color="TIPO_VEICULO",
                      title="Espécie × tipo de veículo (top 6×6)",
                      labels={"qtd": "Multas"})
        fig3.update_layout(height=340, margin=dict(t=50, b=40))
        display(fig3)

        # (4) top 10 marcas
        ma = (aplicar(D["veiculo_marca"]).groupby("NOME_VEICULO_MARCA", as_index=False)["qtd"].sum())
        ma["NOME_VEICULO_MARCA"] = ma["NOME_VEICULO_MARCA"].fillna("NÃO INFORMADO")
        top_ma = ma.groupby("NOME_VEICULO_MARCA", as_index=False)["qtd"].sum() \
                   .nlargest(10, "qtd").sort_values("qtd")
        fig4 = px.bar(top_ma, x="qtd", y="NOME_VEICULO_MARCA", orientation="h",
                      title="Top 10 marcas de veículo",
                      labels={"qtd": "Multas", "NOME_VEICULO_MARCA": "Marca"})
        fig4.update_layout(height=360, margin=dict(t=50, b=40))
        display(fig4)
        display(HTML("<span style='color:#888;font-size:12px'>"
                     "TIPO_VEICULO ≈ 69% nulo na fonte (era sem esse campo) — "
                     "'NÃO INFORMADO' é esperado.</span>"))


w_ano.observe(desenhar_veiculo, names="value")
w_uf.observe(desenhar_veiculo, names="value")
display(out_v)
desenhar_veiculo()
"""

C_VALIDACAO = """\
# ---- Validação de aceite (Etapa E) ----------------------------------------
for nome, df in D.items():
    s = int(df["qtd"].sum())
    assert s == TOTAL_ESPERADO, f"{nome}: {s} != {TOTAL_ESPERADO}"
assert sorted(D["tempo_diario"]["ANO"].unique()) == list(range(2007, 2026))
assert sorted(D["tempo_diario"]["MES"].unique()) == sorted(ORDEM_MES)
assert len(D) == 13
print("VALIDACAO_ETAPA_E_OK — 13 agregados, soma = 92.215.588, 19 anos, 12 meses")
"""


def main() -> None:
    cells = [
        nbformat.v4.new_markdown_cell(MD_INTRO),
        nbformat.v4.new_code_cell(C_SETUP),
        nbformat.v4.new_code_cell(C_FILTROS),
        nbformat.v4.new_code_cell(C_KPI),
        nbformat.v4.new_code_cell(C_TEMPORAL),
        nbformat.v4.new_code_cell(C_GEO),
        nbformat.v4.new_code_cell(C_INFRACAO),
        nbformat.v4.new_code_cell(C_VEICULO),
        nbformat.v4.new_code_cell(C_VALIDACAO),
    ]
    nb = nbformat.v4.new_notebook(cells=cells)
    nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python",
                              "name": "python3"}
    print(f"gerando {SAIDA.name} ({len(cells)} células) e executando...", flush=True)
    client = NotebookClient(nb, timeout=180, kernel_name="python3",
                            resources={"metadata": {"path": str(SAIDA.parent)}})
    client.execute()   # levanta CellExecutionError se alguma célula falhar
    nbformat.write(nb, SAIDA)

    n_code = sum(1 for c in nb.cells if c.cell_type == "code")
    erros = [c for c in nb.cells if c.cell_type == "code"
             and c.get("outputs")
             and any(o.get("output_type") == "error" for o in c["outputs"])]
    print(f"EXEC_OK — {n_code} code cells, {len(erros)} com erro, salvo em {SAIDA}")


if __name__ == "__main__":
    main()
