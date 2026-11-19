"""Cap. 4: spatial patterns."""

import streamlit as st

import charts
import ui
from data import (PERIODOS, area_share, drop_atypical, fmt_int, fmt_pct, mark_periods,
                  mark_years)

PRECISAO = {"street": "Rua + número", "street_nonum": "Rua", "loteamento": "Loteamento",
            "bairro": "Bairro"}
# Fixed zone order (entity, not rank); the 7 processes in rare zones fold to gray.
ZONAS = ["ZR-1", "ZR-2", "ZR-3"]


def render(df, df_all, anos, ocultar):
    c1, c2 = st.columns([1, 1])
    with c1:
        modo = ui.segmented(list(charts.MAP_MODES), key="modo_mapa")
    with c2:
        prec = st.multiselect("Precisão mínima da localização", list(PRECISAO),
                              default=["street", "street_nonum"], format_func=PRECISAO.get,
                              help="Pontos por bairro ou loteamento caem no centroide e criam "
                                   "falsas concentrações.")
    pts = df[df["geocode_precision"].isin(prec)]
    charts.mapa(pts, modo)
    if charts.MAP_MODES[modo] == "pontos":
        legenda = " · ".join(f"<span style='color:rgb{tuple(v)}'>●</span> {k}"
                             for k, v in charts.MACRO_RGB.items())
        st.caption(f"{legenda}. Raio proporcional à raiz da área; {fmt_int(len(pts))} pontos.",
                   unsafe_allow_html=True)

    ui.heading("Área requerida por bairro e período")
    base = drop_atypical(df, "area", ocultar)
    top = base.groupby("bairro_macro")["metragem_m2"].sum().nlargest(12).index
    hm = (base[base["bairro_macro"].isin(top)].groupby(["periodo", "bairro_macro"])["metragem_m2"]
          .sum().div(1000).reset_index(name="mil_m2"))
    hm = hm if ocultar else mark_periods(hm)
    with ui.chart_box(hm, "bairro_periodo"):
        charts.show(charts.heatmap(hm, "periodo", "bairro_macro", "mil_m2", "Mil m²",
                                   x_sort=PERIODOS, y_sort=list(top)))

    total = df["metragem_m2"].sum()
    mp = df.loc[df["bairro_macro"] == "MEIA PRAIA", "metragem_m2"].sum()
    rank = df.groupby("bairro_macro")["metragem_m2"].sum().sort_values(ascending=False)
    lines = [f"Meia Praia concentra **{fmt_pct(mp / total if total else None)}** da área requerida "
             f"({fmt_int(mp / 1000)} mil m²)."]
    if len(rank) >= 3:
        lines.append(f"Maiores em área: **{rank.index[0].title()}**, **{rank.index[1].title()}** e "
                     f"**{rank.index[2].title()}**.")
    ui.findings(lines, key="espaco")

    c1, c2 = st.columns(2)
    with c1:
        ui.heading("Participação da Meia Praia na área anual")
        share = mark_years(area_share(df, df["bairro_macro"] == "MEIA PRAIA", "ano", "meia_praia"),
                           "area", ocultar)
        with ui.chart_box(share, "meia_praia"):
            charts.show(charts.line_ano(share, "meia_praia", "Meia Praia (%)", fmt=".0%",
                                        y_format="%", domain=[0, 1]))
    with c2:
        ui.heading("Processos por zona, desde 2014")
        z = df[(df["zona"] != "") & (df["ano"] >= 2014)]
        if z.empty:
            ui.empty("Sem zoneamento registrado na seleção.")
        else:
            zona = z["zona"].where(z["zona"].isin(ZONAS), "Outras zonas")
            zl = mark_years(z.assign(zona=zona).groupby(["ano", "zona"]).size()
                            .reset_index(name="processos"), "contagem", ocultar)
            cores = dict(zip(ZONAS, charts.CAT)) | {"Outras zonas": charts.GRAY}
            with ui.chart_box(zl, "zonas"):
                charts.show(charts.stacked_ano(zl, "processos", "zona", "Processos", cores))
            st.caption("O zoneamento só é registrado de forma sistemática a partir de 2014.")

    ui.note("Notas de método",
            "Coordenadas do Nominatim/OpenStreetMap, em camadas de precisão. Bairros homônimos com "
            "códigos distintos (Meia Praia, Morretes - Zona 3) foram agregados.")
