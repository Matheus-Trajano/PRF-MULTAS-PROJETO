#!/usr/bin/env python3
"""
apps/dashboard.py — Fase 3, Etapa E2: dashboard Dash (clique real de drill).

Ciclo completo da especificação docs/especificacao_interacoes.md (Etapa D):
filtros globais ANO/UF + período (temporal) + natureza (infração) +
município (geografia), botão "limpar", KPIs sincronizados, 4 abas e
cascata ano→mês→semana→dia com clique na barra + breadcrumb + "voltar".

Fonte única: dados_tratados/agregados/*.parquet (13 tabelas; soma(qtd)
= 92.215.588) — nunca as 92 M linhas.

Uso:
    .venv/bin/python apps/dashboard.py            # http://0.0.0.0:8050
Requer previamente:
    scripts/04_tratar.py → 05_enriquecer.py → 06_agregar.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback, ctx, dcc, html, no_update

# ── dados ────────────────────────────────────────────────────────────────
RAIZ = Path(__file__).resolve().parent.parent
AGG = RAIZ / "dados_tratados" / "agregados"
TOTAL_ESPERADO = 92_215_588

ORDEM_MES = ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO",
             "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
ORDEM_DIA = ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA", "SABADO", "DOMINGO"]
ORDEM_TURNO = ["MADRUGADA", "MANHA", "TARDE", "NOITE"]
ORDEM_FAIXA = ["00-40", "41-60", "61-80", "81-100", "101-120", "120+",
               "NAO_INFORMADO"]

px.defaults.template = "plotly_white"
_con = duckdb.connect(":memory:")
_con.execute("SET threads=2")
_con.execute("SET memory_limit='1500MB'")


def _ler(nome: str) -> pd.DataFrame:
    return _con.execute(
        f"SELECT * FROM read_parquet('{AGG / (nome + '.parquet')}')"
    ).df()


NOMES = ["tempo_diario", "hora_diaria", "top_infracao", "top_br", "top_uf",
         "top_municipio", "origem_ocorrencia", "natureza", "veiculo_especie",
         "veiculo_marca", "abordagem", "velocidade_faixa", "km_faixa"]
D = {n: _ler(n) for n in NOMES}
for _n, _df in D.items():
    _s = int(_df["qtd"].sum())
    if _s != TOTAL_ESPERADO:
        raise AssertionError(f"{_n}: soma(qtd)={_s} != {TOTAL_ESPERADO}")

TEMPO = D["tempo_diario"]
_DATA_MIN = TEMPO["DATA_INFRACAO"].min()
_DATA_MAX = TEMPO["DATA_INFRACAO"].max()
_DIAS = int((_DATA_MAX - _DATA_MIN).days)

ANOS = sorted(int(a) for a in D["top_uf"]["ANO"].unique())
UFS = sorted(D["top_uf"]["UF_INFRACAO"].dropna().unique().tolist())
NATUREZAS = sorted(D["natureza"]["NATUREZA_INFRA"].dropna().unique().tolist())

H = {"display": "flex", "gap": "10px", "flex-wrap": "wrap"}
CARD = {"border": "1px solid #ddd", "border-radius": "8px",
        "padding": "8px 14px", "background": "#f8f9fa", "min-width": "130px"}
_L = dict(height=340, margin=dict(t=50, b=40))


def _fmt(n) -> str:
    return f"{int(n):,}".replace(",", ".")


# ── filtros ──────────────────────────────────────────────────────────────
def _filtros(df: pd.DataFrame, periodo=False, mun=False, nat=False) -> pd.DataFrame:
    """ANO/UF sempre (quando a coluna existe); demais conforme o painel."""
    out = df
    if "ANO" in out.columns and ANO_SEL:
        out = out[out["ANO"].isin(ANO_SEL)]
    if "UF_INFRACAO" in out.columns and UF_SEL:
        out = out[out["UF_INFRACAO"] == UF_SEL]
    if mun and "NOM_MUNICIPIO" in out.columns and MUN_SEL:
        out = out[out["NOM_MUNICIPIO"] == MUN_SEL]
    if nat and "NATUREZA_INFRA" in out.columns and NAT_SEL:
        out = out[out["NATUREZA_INFRA"] == NAT_SEL]
    if periodo and "DATA_INFRACAO" in out.columns:
        d0, d1 = _periodo_datas()
        out = out[(out["DATA_INFRACAO"] >= d0) & (out["DATA_INFRACAO"] <= d1)]
    return out


# estado espelho dos widgets (atualizado nos callbacks; leitura fora deles)
ANO_SEL: list = []
UF_SEL: str | None = None
MUN_SEL: str | None = None
NAT_SEL: str | None = None
_PERIODO: tuple[pd.Timestamp, pd.Timestamp] | None = None


def _periodo_datas() -> tuple[pd.Timestamp, pd.Timestamp]:
    if _PERIODO is None:
        return _DATA_MIN, _DATA_MAX
    return _PERIODO


def _sincroniza(ano, uf, mun, nat, periodo):
    """Grava o estado dos filtros nas variáveis-módulo lidas por _filtros."""
    global ANO_SEL, UF_SEL, MUN_SEL, NAT_SEL, _PERIODO
    ANO_SEL = [int(a) for a in (ano or [])]
    UF_SEL = uf or None
    MUN_SEL = mun or None
    NAT_SEL = nat or None
    if periodo and len(periodo) == 2:
        _PERIODO = (_DATA_MIN + pd.Timedelta(days=int(periodo[0])),
                    _DATA_MIN + pd.Timedelta(days=int(periodo[1])))
    else:
        _PERIODO = None


# ── figuras ──────────────────────────────────────────────────────────────
def figs_temporal(drill: dict) -> tuple[str, list]:
    """Cascata (nível por clique) + 5 figuras complementares."""
    t = _filtros(TEMPO, periodo=True)
    ano_d, mes_d, sem_d = drill.get("ano"), drill.get("mes"), drill.get("sem")
    if len(t) == 0:
        vazio = go.Figure().update_layout(
            title="Sem dados para os filtros atuais", annotations=[dict(
                text="Ajuste os filtros acima", xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False)])
        return "Sem dados para os filtros atuais", [vazio] * 6

    if sem_d is not None and ano_d and mes_d:
        g = (t[(t["ANO"] == ano_d) & (t["MES"] == mes_d) &
               (t["SEMANA_DO_MES"] == sem_d)]
             .groupby("DATA_INFRACAO", as_index=False)["qtd"].sum()
             .sort_values("DATA_INFRACAO"))
        fig = px.bar(g, x="DATA_INFRACAO", y="qtd",
                     title=f"Multas por dia — {ano_d} · {mes_d} · semana {sem_d}",
                     labels={"qtd": "Multas", "DATA_INFRACAO": "Data"})
        trilha = f"Todos › {ano_d} › {mes_d} › semana {sem_d} › dias"
    elif mes_d is not None:
        base = t[t["MES"] == mes_d]
        if ano_d:
            base = base[base["ANO"] == ano_d]
        g = (base.groupby("SEMANA_DO_MES", as_index=False)["qtd"].sum()
             .sort_values("SEMANA_DO_MES"))
        fig = px.bar(g, x="SEMANA_DO_MES", y="qtd",
                     title=f"Multas por semana do mês — {mes_d}"
                           + (f" · {ano_d}" if ano_d else ""),
                     labels={"qtd": "Multas", "SEMANA_DO_MES": "Semana do mês"})
        trilha = (f"Todos › {str(ano_d) + ' › ' if ano_d else ''}"
                  f"{mes_d} › todas as semanas")
    elif ano_d is not None:
        g = (t[t["ANO"] == ano_d].groupby("MES", as_index=False)["qtd"].sum()
             .assign(MES=lambda d: pd.Categorical(d["MES"], ORDEM_MES, ordered=True))
             .sort_values("MES"))
        fig = px.bar(g, x="MES", y="qtd", title=f"Multas por mês — {ano_d}",
                     labels={"qtd": "Multas", "MES": "Mês"})
        trilha = f"Todos › {ano_d} › todos os meses"
    elif ANO_SEL:
        g = (t.groupby("MES", as_index=False)["qtd"].sum()
             .assign(MES=lambda d: pd.Categorical(d["MES"], ORDEM_MES, ordered=True))
             .sort_values("MES"))
        rot = ", ".join(str(a) for a in ANO_SEL)
        fig = px.bar(g, x="MES", y="qtd", title=f"Multas por mês — {rot}",
                     labels={"qtd": "Multas", "MES": "Mês"})
        trilha = f"Todos › {rot} › todos os meses"
    else:
        g = (t.groupby("ANO", as_index=False)["qtd"].sum().sort_values("ANO"))
        fig = px.bar(g, x="ANO", y="qtd", title="Multas por ano",
                     labels={"qtd": "Multas", "ANO": "Ano"})
        trilha = "Todos os anos"
    fig.update_layout(**_L)

    piv = (t.pivot_table(index="ANO", columns="MES", values="qtd",
                         aggfunc="sum", fill_value=0)
             .reindex(columns=ORDEM_MES, fill_value=0))
    f_heat = px.imshow(piv.values, x=ORDEM_MES, y=[str(a) for a in piv.index],
                       labels=dict(x="Mês", y="Ano", color="Multas"),
                       title="Multas por ano × mês", color_continuous_scale="Blues",
                       aspect="auto", text_auto=".2s")
    f_heat.update_layout(height=380, margin=dict(t=50, b=40))

    g3 = (t.groupby(["DIA_SEMANA_NUM", "DIA_SEMANA"], as_index=False)["qtd"].sum()
          .sort_values("DIA_SEMANA_NUM"))
    f_dia = px.bar(g3, x="DIA_SEMANA", y="qtd", title="Multas por dia da semana",
                   labels={"qtd": "Multas", "DIA_SEMANA": "Dia"},
                   category_orders={"DIA_SEMANA": ORDEM_DIA})
    f_dia.update_layout(height=300, margin=dict(t=50, b=40))

    g4 = t.groupby("FIM_DE_SEMANA")["qtd"].sum().reset_index()
    f_fs = px.pie(g4, names="FIM_DE_SEMANA", values="qtd",
                  title="Fim de semana × dias úteis",
                  color_discrete_map={"SIM": "#ff7f0e", "NAO": "#1f77b4"})
    f_fs.update_layout(height=300, margin=dict(t=50, b=40), legend_title_text="")

    h = _filtros(D["hora_diaria"], periodo=True).groupby("HORA", as_index=False)["qtd"].sum()
    f_hora = px.line(h, x="HORA", y="qtd", markers=True,
                     title="Multas por hora do dia",
                     labels={"qtd": "Multas", "HORA": "Hora"})
    f_hora.update_layout(height=300, margin=dict(t=50, b=40),
                         xaxis=dict(dtick=1, range=[-0.5, 23.5]))

    g6 = (_filtros(D["hora_diaria"], periodo=True).groupby("TURNO", as_index=False)["qtd"].sum()
          .assign(TURNO=lambda d: pd.Categorical(d["TURNO"], ORDEM_TURNO, ordered=True))
          .sort_values("TURNO"))
    f_turno = px.bar(g6, x="TURNO", y="qtd", title="Multas por turno",
                     labels={"qtd": "Multas", "TURNO": "Turno"},
                     color="TURNO", color_discrete_sequence=px.colors.qualitative.Set2)
    f_turno.update_layout(height=300, margin=dict(t=50, b=40), showlegend=False)

    return trilha, [fig, f_heat, f_dia, f_fs, f_hora, f_turno]


def figs_geo() -> list:
    m = _filtros(D["top_municipio"], mun=True).groupby(
        ["UF_INFRACAO", "NOM_MUNICIPIO"], as_index=False)["qtd"].sum()
    m["NOM_MUNICIPIO"] = m["NOM_MUNICIPIO"].fillna("NÃO INFORMADO")
    m["rot"] = m["NOM_MUNICIPIO"] + " (" + m["UF_INFRACAO"].fillna("??") + ")"
    top10 = m[m["NOM_MUNICIPIO"] != "NÃO INFORMADO"].nlargest(10, "qtd").sort_values("qtd")
    f1 = px.bar(top10, x="qtd", y="rot", orientation="h",
                title="Top 10 municípios",
                labels={"qtd": "Multas", "rot": "Município (UF)"})
    f1.update_layout(height=360, margin=dict(t=50, b=40))

    u = _filtros(D["top_uf"]).groupby("UF_INFRACAO", as_index=False)["qtd"].sum()
    u = u.sort_values("qtd", ascending=False)
    f2 = px.bar(u, x="UF_INFRACAO", y="qtd", title="Multas por UF de infração",
                labels={"qtd": "Multas", "UF_INFRACAO": "UF"})
    f2.update_layout(height=320, margin=dict(t=50, b=40))

    o = _filtros(D["origem_ocorrencia"]).copy()
    o["UF_PLACA"] = o["UF_PLACA"].fillna("NÃO INFORMADO")
    o["UF_INFRACAO"] = o["UF_INFRACAO"].fillna("NÃO INFORMADO")
    mat = o.pivot_table(index="UF_PLACA", columns="UF_INFRACAO",
                        values="qtd", aggfunc="sum", fill_value=0)
    f3 = px.imshow(np.log1p(mat.values), x=list(mat.columns), y=list(mat.index),
                   labels=dict(x="UF da infração", y="UF da placa",
                               color="log(1+multas)"),
                   title="UF da placa × UF da infração",
                   color_continuous_scale="Viridis", aspect="auto")
    f3.update_layout(height=520, margin=dict(t=50, b=40))

    tre = m[m["NOM_MUNICIPIO"] != "NÃO INFORMADO"].nlargest(300, "qtd")
    f4 = px.treemap(tre, path=["UF_INFRACAO", "NOM_MUNICIPIO"], values="qtd",
                    title="Drill UF → município (clique p/ expandir)",
                    color="qtd", color_continuous_scale="Blues")
    f4.update_layout(height=440, margin=dict(t=50, b=40))

    b = _filtros(D["top_br"]).groupby(["NUM_BR_INFRACAO", "BR_FORMATADA"],
                                       as_index=False)["qtd"].sum()
    b["rot"] = b["BR_FORMATADA"].fillna("SEM BR")
    top_br = b.nlargest(10, "qtd").sort_values("qtd")
    f5 = px.bar(top_br, x="qtd", y="rot", orientation="h", title="Top 10 BRs",
                labels={"qtd": "Multas", "rot": "BR"})
    f5.update_layout(height=320, margin=dict(t=50, b=40))

    k = _filtros(D["km_faixa"]).groupby("FAIXA_KM", as_index=False)["qtd"].sum()
    k = k.sort_values("FAIXA_KM")
    f6 = px.bar(k, x="FAIXA_KM", y="qtd",
                title="Distribuição por faixa de KM da infração",
                labels={"qtd": "Multas", "FAIXA_KM": "Faixa de KM"})
    f6.update_layout(height=340, margin=dict(t=50, b=40))

    kb = _filtros(D["km_faixa"]).copy()
    kb["rot"] = kb["BR_FORMATADA"].fillna("SEM BR")
    top12 = kb.groupby("rot")["qtd"].sum().nlargest(12).index.tolist()
    matk = (kb[kb["rot"].isin(top12)]
            .pivot_table(index="rot", columns="FAIXA_KM", values="qtd",
                         aggfunc="sum", fill_value=0))
    matk = matk.reindex(sorted(matk.columns), axis=1)
    f7 = px.imshow(np.log1p(matk.values), x=list(matk.columns), y=list(matk.index),
                   labels=dict(x="Faixa de KM", y="BR", color="log(1+multas)"),
                   title="KM por BR — top 12 BRs",
                   color_continuous_scale="Greens", aspect="auto")
    f7.update_layout(height=420, margin=dict(t=50, b=40))
    return [f1, f2, f3, f4, f5, f6, f7]


def figs_infracao() -> list:
    d = _filtros(D["top_infracao"], nat=True).groupby(
        "DESCRICAO_ABRVIADA", as_index=False)["qtd"].sum()
    top = d.nlargest(10, "qtd").sort_values("qtd")
    f1 = px.bar(top, x="qtd", y="DESCRICAO_ABRVIADA", orientation="h",
                title="Top 10 infrações mais autuadas",
                labels={"qtd": "Multas", "DESCRICAO_ABRVIADA": "Descrição"})
    f1.update_layout(height=380, margin=dict(t=50, b=40))

    n = (_filtros(D["natureza"], nat=True).groupby("NATUREZA_INFRA", as_index=False)["qtd"].sum()
         .sort_values("qtd", ascending=False))
    f2 = px.bar(n, x="NATUREZA_INFRA", y="qtd", title="Multas por natureza",
                labels={"qtd": "Multas", "NATUREZA_INFRA": "Natureza"},
                color="NATUREZA_INFRA",
                color_discrete_sequence=px.colors.qualitative.Set2)
    f2.update_layout(height=320, margin=dict(t=50, b=40), showlegend=False)

    v = (_filtros(D["velocidade_faixa"], nat=True)
         .groupby("FAIXA_VELOCIDADE", as_index=False)["qtd"].sum()
         .assign(F=lambda d: pd.Categorical(d["FAIXA_VELOCIDADE"],
                                            ORDEM_FAIXA, ordered=True))
         .sort_values("F"))
    f3 = px.bar(v, x="FAIXA_VELOCIDADE", y="qtd",
                title="Multas por faixa de velocidade medida",
                labels={"qtd": "Multas", "FAIXA_VELOCIDADE": "Faixa (km/h)"})
    f3.update_layout(height=320, margin=dict(t=50, b=40))

    e = (_filtros(D["top_infracao"], nat=True)
         .groupby(["ENQUADRAMENTO", "DESCRICAO_ABRVIADA"], as_index=False)["qtd"].sum()
         .nlargest(150, "qtd"))
    e["ENQUADRAMENTO"] = e["ENQUADRAMENTO"].fillna("SEM ENQUADRAMENTO")
    f4 = px.treemap(e, path=["ENQUADRAMENTO", "DESCRICAO_ABRVIADA"], values="qtd",
                    title="Drill enquadramento → descrição (clique p/ expandir)",
                    color="qtd", color_continuous_scale="Reds")
    f4.update_layout(height=440, margin=dict(t=50, b=40))

    a = (_filtros(D["abordagem"], nat=True)
         .groupby(["TIP_ABORDAGEM", "IND_ASSINOU_AUTO"], as_index=False)["qtd"].sum())
    a["TIP_ABORDAGEM"] = a["TIP_ABORDAGEM"].fillna("NÃO INFORMADO")
    a["IND_ASSINOU_AUTO"] = a["IND_ASSINOU_AUTO"].fillna("NÃO INFORMADO")
    f5 = px.bar(a, x="TIP_ABORDAGEM", y="qtd", color="IND_ASSINOU_AUTO",
                title="Tipo de abordagem × assinatura do auto",
                labels={"qtd": "Multas", "IND_ASSINOU_AUTO": "Assinou"})
    f5.update_layout(height=320, margin=dict(t=50, b=40))
    return [f1, f2, f3, f4, f5]


def figs_veiculo() -> list:
    ve = _filtros(D["veiculo_especie"]).copy()
    ve["ESPECIE"] = ve["ESPECIE"].fillna("NÃO INFORMADO")
    ve["TIPO_VEICULO"] = ve["TIPO_VEICULO"].fillna("NÃO INFORMADO")

    e = ve.groupby("ESPECIE", as_index=False)["qtd"].sum().sort_values(
        "qtd", ascending=False)
    f1 = px.bar(e, x="ESPECIE", y="qtd", title="Multas por espécie de veículo",
                labels={"qtd": "Multas", "ESPECIE": "Espécie"})
    f1.update_layout(height=320, margin=dict(t=50, b=40))

    tv = (ve.groupby("TIPO_VEICULO", as_index=False)["qtd"].sum()
          .nlargest(12, "qtd").sort_values("qtd"))
    f2 = px.bar(tv, x="qtd", y="TIPO_VEICULO", orientation="h",
                title="Top 12 tipos de veículo",
                labels={"qtd": "Multas", "TIPO_VEICULO": "Tipo"})
    f2.update_layout(height=380, margin=dict(t=50, b=40))

    st = ve.groupby(["ESPECIE", "TIPO_VEICULO"], as_index=False)["qtd"].sum()
    top_t = st.groupby("TIPO_VEICULO")["qtd"].sum().nlargest(6).index
    st = st[st["TIPO_VEICULO"].isin(top_t)]
    st = st[st["ESPECIE"].isin(st.groupby("ESPECIE")["qtd"].sum().nlargest(6).index)]
    f3 = px.bar(st, x="ESPECIE", y="qtd", color="TIPO_VEICULO",
                title="Espécie × tipo de veículo (top 6×6)",
                labels={"qtd": "Multas"})
    f3.update_layout(height=340, margin=dict(t=50, b=40))

    ma = _filtros(D["veiculo_marca"]).groupby(
        "NOME_VEICULO_MARCA", as_index=False)["qtd"].sum()
    ma["NOME_VEICULO_MARCA"] = ma["NOME_VEICULO_MARCA"].fillna("NÃO INFORMADO")
    ma = ma.groupby("NOME_VEICULO_MARCA", as_index=False)["qtd"].sum() \
           .nlargest(10, "qtd").sort_values("qtd")
    f4 = px.bar(ma, x="qtd", y="NOME_VEICULO_MARCA", orientation="h",
                title="Top 10 marcas de veículo",
                labels={"qtd": "Multas", "NOME_VEICULO_MARCA": "Marca"})
    f4.update_layout(height=360, margin=dict(t=50, b=40))
    return [f1, f2, f3, f4]


def kpis_html(ano, uf, periodo) -> str:
    _sincroniza(ano, uf, None, None, periodo)
    t = _filtros(TEMPO, periodo=True)
    total = int(t["qtd"].sum())
    dias = t["DATA_INFRACAO"].nunique()
    media = total / dias if dias else 0
    if total:
        por_dia = t.groupby("DATA_INFRACAO")["qtd"].sum()
        pico, pico_v = por_dia.idxmax(), int(por_dia.max())
    else:
        pico, pico_v = "-", 0
    fimsemana = int(t.loc[t["FIM_DE_SEMANA"] == "SIM", "qtd"].sum())
    share = 100 * fimsemana / total if total else 0
    ufs = _filtros(D["top_uf"])["UF_INFRACAO"].nunique()
    cards = [
        ("Multas (filtro atual)", _fmt(total)),
        ("% do total (92.215.588)", f"{100 * total / TOTAL_ESPERADO:.1f}%"),
        ("Dias com dados", _fmt(dias)),
        ("Média/dia", _fmt(round(media))),
        ("Pico (dia)", f"{pico:%d/%m/%Y} · {_fmt(pico_v)}" if total else "-"),
        ("Fim de semana", f"{share:.1f}%"),
        ("UFs no filtro", _fmt(ufs)),
    ]
    return ("<div style='" + ";".join(f"{k}:{v}" for k, v in H.items()) + "'>"
            + "".join(
                f"<div style='{';'.join(f'{k}:{v}' for k, v in CARD.items())}'>"
                f"<div style='font-size:11px;color:#666'>{k}</div>"
                f"<div style='font-size:18px;font-weight:600'>{v}</div></div>"
                for k, v in cards)
            + "</div>")


# ── layout ───────────────────────────────────────────────────────────────
def _graf(id_: str, altura: int = 340) -> dcc.Graph:
    return dcc.Graph(id=id_, config={"displaylogo": False})


app = Dash(__name__, title="PRF Multas — EDA (Fase 3)")
app.layout = html.Div([
    html.Div([
        html.H2("🚦 Multas da PRF — 2007–2025", style={"margin": "0"}),
        html.Div("92.215.588 registros · 13 agregados · filtros globais abaixo "
                 "→ todos os painéis se re-renderizam · jun/2024 não existe "
                 "na fonte (não é falha)", style={"color": "#666", "font-size": "13px"}),
    ], style={"margin": "10px 16px"}),

    html.Div([
        dcc.Dropdown(id="f-ano", multi=True, placeholder="ANO: todos",
                     options=[{"label": str(a), "value": a} for a in ANOS],
                     style={"min-width": "230px"}),
        dcc.Dropdown(id="f-uf", placeholder="UF: todas",
                     options=[{"label": u, "value": u} for u in UFS],
                     style={"min-width": "170px"}),
        dcc.Dropdown(id="f-mun", placeholder="Município (selecione a UF)",
                     disabled=True, style={"min-width": "240px"}),
        dcc.Dropdown(id="f-nat", placeholder="Natureza: todas",
                     options=[{"label": n, "value": n} for n in NATUREZAS],
                     style={"min-width": "210px"}),
        html.Div([
            html.Label("Período (afeta temporal e KPIs)",
                       style={"font-size": "11px", "color": "#666"}),
            dcc.RangeSlider(id="f-periodo", min=0, max=_DIAS, step=1,
                            value=[0, _DIAS],
                            marks={i * 365: str(2007 + i)
                                   for i in range(19) if i * 365 <= _DIAS},
                            tooltip={"placement": "bottom"},
                            updatemode="drag"),
        ], style={"min-width": "320px", "flex": "1"}),
        html.Button("🧹 Limpar filtros", id="btn-limpar", n_clicks=0,
                    style={"align-self": "center"}),
    ], style={**H, "margin": "6px 16px", "align-items": "center",
              "padding": "8px", "background": "#f1f3f5", "border-radius": "8px"}),

    html.Div(id="kpi-row", style={"margin": "8px 16px"}),

    dcc.Store(id="drill", data={"ano": None, "mes": None, "sem": None}),

    dcc.Tabs(id="abas", value="aba-temp", children=[
        dcc.Tab(label="⏱ Temporal", value="aba-temp", children=[
            html.Div([
                html.Div([
                    html.Span(id="breadcrumb", style={"font-size": "14px", "font-weight": "600"}),
                    html.Button("⬆ voltar um nível", id="btn-voltar",
                                n_clicks=0, style={"margin-left": "12px"}),
                ], style={"margin": "10px 16px 0"}),
                _graf("g-cascata"),
                _graf("g-heat", 380),
                html.Div([_graf("g-dia", 300), _graf("g-fs", 300)], style=H),
                html.Div([_graf("g-hora", 300), _graf("g-turno", 300)], style=H),
            ]),
        ]),
        dcc.Tab(label="🗺 Geográfica", value="aba-geo", children=[
            html.Div([
                html.Div([_graf("g-mun", 360), _graf("g-uf", 320)], style=H),
                _graf("g-matriz", 520),
                _graf("g-treemap", 440),
                html.Div([_graf("g-br", 320), _graf("g-km", 340)], style=H),
                _graf("g-kmbr", 420),
            ], style={"margin": "8px 16px"}),
        ]),
        dcc.Tab(label="🚨 Infração", value="aba-inf", children=[
            html.Div([
                _graf("g-desc", 380),
                html.Div([_graf("g-nat", 320), _graf("g-vel", 320)], style=H),
                _graf("g-enq", 440),
                _graf("g-abord", 320),
            ], style={"margin": "8px 16px"}),
        ]),
        dcc.Tab(label="🚗 Veículo", value="aba-vei", children=[
            html.Div([
                html.Div([_graf("g-esp", 320), _graf("g-tipo", 380)], style=H),
                _graf("g-epitipo", 340),
                _graf("g-marcas", 360),
            ], style={"margin": "8px 16px"}),
        ]),
    ]),
], style={"font-family": "Segoe UI, sans-serif", "max-width": "1280px",
          "margin": "0 auto"})


# ── callbacks ────────────────────────────────────────────────────────────
@callback(Output("f-mun", "options"), Output("f-mun", "disabled"),
          Output("f-mun", "value"),
          Input("f-uf", "value"))
def opcoes_municipio(uf):
    if not uf:
        return [], True, None
    m = D["top_municipio"]
    m = m[m["UF_INFRACAO"] == uf]
    opts = sorted(m["NOM_MUNICIPIO"].dropna().unique().tolist())
    return [{"label": x, "value": x} for x in opts], False, None


@callback(Output("f-ano", "value"), Output("f-uf", "value"),
          Output("f-nat", "value"), Output("f-periodo", "value"),
          Output("drill", "data"),
          Input("btn-limpar", "n_clicks"),
          State("f-ano", "value"), State("f-uf", "value"),
          State("f-nat", "value"), State("f-periodo", "value"),
          prevent_initial_call=True)
def limpar(n, ano, uf, nat, per):
    if not n:
        return no_update, no_update, no_update, no_update, no_update
    return None, None, None, [0, _DIAS], {"ano": None, "mes": None, "sem": None}


@callback(Output("drill", "data", allow_duplicate=True),
          Input("g-cascata", "clickData"),
          Input("btn-voltar", "n_clicks"),
          Input("f-ano", "value"),
          State("drill", "data"),
          prevent_initial_call=True)
def navega_drill(click, voltar, ano_global, drill):
    drill = dict(drill or {"ano": None, "mes": None, "sem": None})
    trig = ctx.triggered_id
    if trig == "f-ano":
        # mudou o filtro global → recomeça a cascata
        return {"ano": None, "mes": None, "sem": None}
    if trig == "btn-voltar":
        if drill["sem"] is not None:
            drill["sem"] = None
        elif drill["mes"] is not None:
            drill["mes"] = None
        elif drill["ano"] is not None:
            drill["ano"] = None
        return drill
    if trig == "g-cascata" and click:
        x = click["points"][0].get("x")
        if drill["ano"] is None and drill["mes"] is None and drill["sem"] is None:
            if ano_global:
                # vista de meses → clique no mês
                if isinstance(x, str) and x.upper() in ORDEM_MES:
                    drill["mes"] = x.upper()
            else:
                # vista de anos → clique no ano
                try:
                    drill["ano"] = int(x)
                except (TypeError, ValueError):
                    return no_update
        elif drill["ano"] is not None and drill["mes"] is None:
            if isinstance(x, str) and x.upper() in ORDEM_MES:
                drill["mes"] = x.upper()
        elif drill["mes"] is not None and drill["sem"] is None:
            try:
                drill["sem"] = int(x)
            except (TypeError, ValueError):
                return no_update
        # nível dia: folha, nada a fazer
        return drill
    return no_update


@callback(Output("kpi-row", "children"),
          Input("f-ano", "value"), Input("f-uf", "value"),
          Input("f-periodo", "value"))
def atualiza_kpis(ano, uf, per):
    return dcc.HTML(kpis_html(ano, uf, per))


@callback(Output("breadcrumb", "children"),
          Output("g-cascata", "figure"), Output("g-heat", "figure"),
          Output("g-dia", "figure"), Output("g-fs", "figure"),
          Output("g-hora", "figure"), Output("g-turno", "figure"),
          Input("f-ano", "value"), Input("f-uf", "value"),
          Input("f-periodo", "value"), Input("drill", "data"))
def render_temporal(ano, uf, per, drill):
    _sincroniza(ano, uf, None, None, per)
    trilha, figs = figs_temporal(drill or {})
    return trilha, *figs


@callback(Output("g-mun", "figure"), Output("g-uf", "figure"),
          Output("g-matriz", "figure"), Output("g-treemap", "figure"),
          Output("g-br", "figure"), Output("g-km", "figure"),
          Output("g-kmbr", "figure"),
          Input("f-ano", "value"), Input("f-uf", "value"),
          Input("f-mun", "value"))
def render_geo(ano, uf, mun):
    _sincroniza(ano, uf, mun, None, None)
    return tuple(figs_geo())


@callback(Output("g-desc", "figure"), Output("g-nat", "figure"),
          Output("g-vel", "figure"), Output("g-enq", "figure"),
          Output("g-abord", "figure"),
          Input("f-ano", "value"), Input("f-uf", "value"),
          Input("f-nat", "value"))
def render_infracao(ano, uf, nat):
    _sincroniza(ano, uf, None, nat, None)
    return tuple(figs_infracao())


@callback(Output("g-esp", "figure"), Output("g-tipo", "figure"),
          Output("g-epitipo", "figure"), Output("g-marcas", "figure"),
          Input("f-ano", "value"), Input("f-uf", "value"))
def render_veiculo(ano, uf):
    _sincroniza(ano, uf, None, None, None)
    return tuple(figs_veiculo())


def main() -> None:
    print(f"agregados OK: {len(D)} tabelas, soma = {TOTAL_ESPERADO:,}")
    app.run(host="0.0.0.0", port=8050, debug=False)


if __name__ == "__main__":
    main()
