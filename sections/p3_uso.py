"""Cap. 3: land use and verticalization."""

import streamlit as st

import charts
import ui
from data import (PERIODOS, area_share, drop_atypical, fmt_int, fmt_pct, mark_periods,
                  mark_years)


def render(df, df_all, anos, ocultar):
    medida = ui.segmented(["Área (m²)", "Nº de processos"], key="medida_uso")
    col, kind = ("area_m2", "area") if medida == "Área (m²)" else ("processos", "contagem")
    long = (df.groupby(["ano", "uso_grupo"])
              .agg(processos=("processo", "size"), area_m2=("metragem_m2", "sum"))
              .reset_index())
    long = mark_years(long[long[col] > 0], kind, ocultar)
    ui.heading("Composição do uso por ano")
    with ui.chart_box(long, "uso_ano"):
        charts.show(charts.stacked_ano(long, col, "uso_grupo", "Participação",
                                       charts.USO_COLORS, normalize=True))

    # Findings from regular years only (no thin or partial year).
    reg = drop_atypical(df, "area", True)
    by_per = area_share(reg, reg["vertical"], "periodo", "vertical").set_index("periodo")["vertical"]
    pers = [p for p in PERIODOS if p in by_per.index]
    sem_info = (reg["uso_grupo"] == "Sem informação").groupby(reg["periodo"]).mean()
    med = reg.groupby("uso_grupo")["metragem_m2"].median()
    lines = []
    if pers:
        lines.append(f"Área vertical: **{fmt_pct(by_per[pers[0]])}** em {pers[0]} e "
                     f"**{fmt_pct(by_per[pers[-1]])}** em {pers[-1]}.")
        lines.append(f"Uso sem informação: **{fmt_pct(sem_info[pers[0]])}** dos processos em {pers[0]} "
                     f"e **{fmt_pct(sem_info[pers[-1]])}** em {pers[-1]}.")
    if {"Multifamiliar", "Unifamiliar"} <= set(med.dropna().index):
        lines.append(f"Mediana: multifamiliar **{fmt_int(med['Multifamiliar'])} m²**, "
                     f"unifamiliar **{fmt_int(med['Unifamiliar'])} m²**.")
    if lines:
        ui.findings(lines, key="uso")

    c1, c2 = st.columns(2)
    with c1:
        ui.heading("Participação vertical na área nova")
        vert = mark_years(area_share(df, df["vertical"], "ano", "vertical"), "area", ocultar)
        with ui.chart_box(vert, "vertical"):
            charts.show(charts.line_ano(vert, "vertical", "Área vertical (%)", fmt=".0%",
                                        color=charts.CAT[1], y_format="%", domain=[0, 1]))
    with c2:
        ui.heading("Tamanho dos projetos por uso")
        d = df[df["metragem_m2"].notna() & (df["uso_grupo"] != "Sem informação")]
        if len(d):
            charts.show(charts.box_log(d, "uso_grupo", "metragem_m2", "Área (m², escala log)",
                                       charts.USO_COLORS))
        else:
            ui.empty("Sem processos com uso e área informados.")

    ui.heading("Área mediana por uso e período (m²)")
    hm = (drop_atypical(df, "area", ocultar).dropna(subset=["metragem_m2"])
          .groupby(["periodo", "uso_grupo"])["metragem_m2"].median().reset_index())
    hm = hm if ocultar else mark_periods(hm)
    with ui.chart_box(hm, "mediana_uso_periodo"):
        charts.show(charts.heatmap(hm, "periodo", "uso_grupo", "metragem_m2", "Mediana (m²)",
                                   x_sort=PERIODOS, y_sort=list(charts.USO_COLORS)))

    ui.note("Notas de método",
            "Vertical = multifamiliar, multifamiliar + comercial e interesse social, sobre a área "
            "informada. Períodos com muito uso sem informação subestimam a verticalização.")
