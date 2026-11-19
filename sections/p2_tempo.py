"""Cap. 2: time dynamics."""

import streamlit as st

import charts
import ui
from data import fmt_int, fmt_pct, mark_years, per_year

METRICAS = {  # label: (column, axis title, format, atypical rule)
    "Nº de processos": ("processos", "Nº de processos", ",.0f", "contagem"),
    "Área total (m²)": ("area_m2", "Área total (m²)", ",.0f", "area"),
    "Área média (m²)": ("area_media", "Área média por processo (m²)", ",.0f", "area"),
}


def render(df, df_all, anos, ocultar):
    py = per_year(df, anos)
    escolha = ui.segmented(list(METRICAS), key="metrica_tempo")
    col, titulo, fmt, kind = METRICAS[escolha]
    serie = mark_years(py[["ano", col]], kind, ocultar)
    with ui.chart_box(serie, "serie_anual"):
        charts.show(charts.bar_ano(serie, col, titulo, fmt=fmt))

    # Findings use regular years only, so a partial or thin year never sets a record.
    cont = mark_years(py, "contagem", False).query("~atipico")
    area = mark_years(py, "area", False).query("~atipico")
    lines = []
    if cont["processos"].sum():
        pk = cont.loc[cont["processos"].idxmax()]
        lines.append(f"Pico de processos: **{fmt_int(pk['processos'])} em {int(pk['ano'])}**.")
    if area["area_m2"].sum():
        pa = area.loc[area["area_m2"].idxmax()]
        lines.append(f"Pico de área: **{fmt_int(pa['area_m2'] / 1000)} mil m² em {int(pa['ano'])}**.")
    a, b = area[area["ano"].between(2015, 2019)], area[area["ano"].between(2020, 2025)]
    if len(a) and len(b) and a["area_m2"].mean():
        var = f"{b['area_m2'].mean() / a['area_m2'].mean() - 1:+.0%}"
        lines.append(f"Área média anual 2020-25 vs 2015-19: **{var}**.")
    if lines:
        ui.findings(lines, key="tempo")

    c1, c2 = st.columns(2)
    with c1:
        ui.heading("Área mediana por processo")
        d = mark_years(py.dropna(subset=["area_mediana"]), "area", ocultar)
        with ui.chart_box(d[["ano", "area_mediana", "com_area"]], "mediana"):
            charts.show(charts.line_ano(d, "area_mediana", "Área mediana (m²)"))
        st.caption("Mediana crescente indica projetos maiores.")
    with c2:
        ui.heading("Taxa de deferimento")
        d = mark_years(py.dropna(subset=["taxa_deferimento"]), "contagem", ocultar)
        with ui.chart_box(d[["ano", "taxa_deferimento", "processos"]], "deferimento"):
            charts.show(charts.line_ano(d, "taxa_deferimento", "Deferidos (%)", fmt=".0%",
                                        color=charts.CAT[3], y_format="%", domain=[0, 1]))
        reg = d[~d["atipico"]]
        taxa = reg["deferidos"].sum() / reg["processos"].sum() if reg["processos"].sum() else None
        st.caption(f"Decisão registrada no processo: {fmt_pct(taxa)} deferidos nos anos regulares.")

    ui.note("Notas de método",
            "Faixas cinza marcam choques econômicos (2008-09, 2014-16, 2020) para leitura de ciclos, "
            "sem implicar causa. Anos atípicos ficam em areia e não entram nos achados.")
