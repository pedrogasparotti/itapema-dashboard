"""Cap. 5: owners/developers and concentration."""

import pandas as pd
import streamlit as st

import charts
import ui
from data import drop_atypical, fmt_int, fmt_pct, gini, hhi, mark_years, top_decile_share

MIN_OWNERS = 20


def concentration(df):
    """Same metric as analyze_report.plot_concentration (plots/04_concentration.png)."""
    rows = []
    for ano, g in df.groupby("ano"):
        m2 = g[g["metragem_m2"] > 0].groupby("owner_code")["metragem_m2"].sum()
        cnt = g.groupby("owner_code").size()
        if m2.size >= MIN_OWNERS and cnt.size >= MIN_OWNERS:
            rows += [{"ano": ano, "indice": "Gini", "valor": gini(m2)},
                     {"ano": ano, "indice": "Participação do decil superior", "valor": top_decile_share(m2)},
                     {"ano": ano, "indice": "HHI", "valor": hhi(m2)}]
    return pd.DataFrame(rows)


def render(df, df_all, anos, ocultar):
    c1, c2 = st.columns(2)
    by = df.groupby("owner_label").agg(area=("metragem_m2", "sum"), processos=("processo", "size"))
    with c1:
        ui.heading("Top 20 requerentes por área")
        t = by["area"].nlargest(20).div(1000).rename("mil_m2").reset_index()
        with ui.chart_box(t, "top_area"):
            charts.show(charts.hbar(t, "owner_label", "mil_m2", "Área total (mil m²)", fmt=",.1f"))
    with c2:
        ui.heading("Top 20 requerentes por nº de processos")
        t = by["processos"].nlargest(20).reset_index()
        with ui.chart_box(t, "top_processos"):
            charts.show(charts.hbar(t, "owner_label", "processos", "Processos", color=charts.CAT[3]))

    ui.heading("Concentração da área por requerente")
    c = concentration(drop_atypical(df, "area", ocultar))
    if c.empty:
        ui.empty(f"Nenhum ano com {MIN_OWNERS} ou mais requerentes na seleção.")
    else:
        cores = {"Gini": charts.CAT[0], "Participação do decil superior": charts.CAT[1], "HHI": charts.CAT[2]}
        with ui.chart_box(c, "concentracao"):
            charts.show(charts.multi_line(c, "valor", "indice", "Índice (0 a 1)", cores, domain=[0, 1]))

    total = df["metragem_m2"].sum()
    top10 = by["area"].nlargest(10).sum()
    pjs = df.loc[df["tipo_requerente"].str.startswith("Pessoa jurídica"), "metragem_m2"].sum()
    lines = [f"Os 10 maiores requerentes somam **{fmt_pct(top10 / total if total else None)}** da área, "
             f"entre {fmt_int(df['owner_code'].nunique())} requerentes.",
             f"Pessoas jurídicas respondem por **{fmt_pct(pjs / total if total else None)}** da área."]
    if not c.empty:
        g = c[c["indice"] == "Gini"].sort_values("ano")
        ini, fim = (f"{v:.2f}".replace(".", ",") for v in (g["valor"].iloc[0], g["valor"].iloc[-1]))
        lines.append(f"Gini da área: **{ini}** em {int(g['ano'].iloc[0])} e **{fim}** em {int(g['ano'].iloc[-1])}.")
    ui.findings(lines, key="agentes")

    c1, c2 = st.columns(2)
    with c1:
        ui.heading("Área por tipo de requerente")
        pj = df.groupby(["ano", "tipo_requerente"])["metragem_m2"].sum().reset_index()
        tot = pj.groupby("ano")["metragem_m2"].transform("sum")
        pj["participacao"] = pj["metragem_m2"] / tot.where(tot > 0)
        pj = mark_years(pj.dropna(subset=["participacao"]), "area", ocultar)
        cores = {"Pessoa jurídica (heurística)": charts.CAT[0],
                 "Pessoa física / não identificado": charts.GRAY}
        with ui.chart_box(pj, "pj"):
            charts.show(charts.stacked_ano(pj, "participacao", "tipo_requerente", "Participação",
                                           cores, normalize=True, fmt=".0%"))
    with c2:
        ui.heading("Requerentes distintos por ano")
        n = mark_years(df.groupby("ano")["owner_code"].nunique().rename("requerentes").reset_index(),
                       "contagem", ocultar)
        with ui.chart_box(n, "requerentes"):
            charts.show(charts.bar_ano(n, "requerentes", "Requerentes distintos", color=charts.CAT[3],
                                       bands=False))

    ui.note("Notas de método",
            f"Requerente identificado pelo código numérico; índices de analyze_report.py em anos com "
            f"{MIN_OWNERS} ou mais requerentes com área. PJ e PF vêm de palavras do nome e são aproximados.")
