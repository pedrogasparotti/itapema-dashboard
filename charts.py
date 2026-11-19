"""Altair/pydeck chart builders: one look for every chapter.

Colours come from collor-pallete-refferences.png, saturated so each slot passes the
dataviz checks on the #F6F1E7 surface (lightness band, chroma floor, adjacent CVD
ΔE >= 8.8). Slots are assigned in fixed order by entity, never by rank; maps use
3 slots + gray. Atypical years (data.atypical_years) are drawn in sand or faded.
"""

import altair as alt
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

from data import USO_GRUPOS

CAT = ["#3557A8", "#D9A23A", "#B03A3E", "#0F8F7A", "#7286D6", "#C8683A", "#7A4E9C", "#6F8F2E"]
GRAY = "#9C968C"            # "Sem informação" / neutral
ATIP = "#BFAE8E"            # atypical years (sand)
SEQ = ["#e6ecf8", "#afc1e7", "#7c96d5", "#5169a8", "#2c3e74", "#1b2a5c"]
USO_COLORS = dict(zip(USO_GRUPOS[:-1], CAT)) | {"Sem informação": GRAY}
MACRO_RGB = {"Unifamiliar": [53, 87, 168], "Multifamiliar": [217, 162, 58],
             "Comercial": [176, 58, 62], "Outros / sem informação": [156, 150, 140]}
SEQ_RGB = [[230, 236, 248], [175, 193, 231], [124, 150, 213], [81, 105, 168],
           [44, 62, 116], [27, 42, 92]]
FADED = 0.35
STATUS = ["Regular", "Ano atípico"]

# Economic shocks annotated on time charts.
BANDAS = pd.DataFrame([
    {"ini": 2008, "fim": 2009, "rotulo": "Crise 2008-09"},
    {"ini": 2014, "fim": 2016, "rotulo": "Recessão 2014-16"},
    {"ini": 2020, "fim": 2020, "rotulo": "Pandemia"},
])

# Lines use a numeric year axis; zero=False keeps the domain on the years.
ANO_X = alt.X("ano:Q", title="Ano do processo", scale=alt.Scale(zero=False),
              axis=alt.Axis(format="d", tickMinStep=1, labelFlush=False, labelOverlap=True))
# Bars use an ordinal year axis: bands size themselves and never include zero.
ANO_O = alt.X("ano:O", title="Ano do processo", axis=alt.Axis(labelAngle=-90))
LEGEND_TOP = dict(orient="top", title=None, labelLimit=320)


def show(chart):
    st.altair_chart(chart, width="stretch")


def _has_atip(df):
    return "atipico" in df and bool(df["atipico"].any())


def _with_status(df):
    out = df.copy()
    if "atipico" not in out:
        out["atipico"], out["motivo"] = False, ""
    out["status"] = np.where(out["atipico"], STATUS[1], STATUS[0])
    return out


def _tip_motivo(df):
    return [alt.Tooltip("motivo:N", title="Ano atípico")] if _has_atip(df) else []


def _bands(years):
    """Shock bands on the ordinal axis, clipped to the years drawn (so no year is added)."""
    rows = []
    for b in BANDAS.itertuples():
        inside = [y for y in years if b.ini <= y <= b.fim]
        if inside:
            rows.append({"ini": inside[0], "fim": inside[-1], "rotulo": b.rotulo})
    b = pd.DataFrame(rows, columns=["ini", "fim", "rotulo"])
    x = alt.X("ini:O", title="Ano do processo", bandPosition=0)
    rect = alt.Chart(b).mark_rect(color=GRAY, opacity=0.12).encode(
        x=x, x2=alt.X2("fim", bandPosition=1), tooltip=[alt.Tooltip("rotulo:N", title="Período")])
    text = alt.Chart(b).mark_text(align="left", baseline="top", dx=3, dy=3, fontSize=10,
                                  color=GRAY).encode(x=x, y=alt.value(0), text="rotulo:N")
    return rect + text


def bar_ano(df, y, y_title, fmt=",.0f", color=CAT[0], bands=True):
    d = _with_status(df)
    legend = alt.Legend(**LEGEND_TOP) if _has_atip(df) else None
    bars = alt.Chart(d).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=ANO_O, y=alt.Y(f"{y}:Q", title=y_title),
        color=alt.Color("status:N", scale=alt.Scale(domain=STATUS, range=[color, ATIP]), legend=legend),
        tooltip=[alt.Tooltip("ano:O", title="Ano"),
                 alt.Tooltip(f"{y}:Q", title=y_title, format=fmt)] + _tip_motivo(df))
    chart = (_bands(sorted(set(d["ano"]))) + bars) if bands and len(d) else bars
    return chart.properties(height=340)


def line_ano(df, y, y_title, fmt=",.0f", color=CAT[0], y_format=None, domain=None):
    """Line through regular years; atypical years as hollow sand points (not joined)."""
    d = _with_status(df)
    scale = alt.Scale(domain=domain) if domain else alt.Undefined
    y_enc = alt.Y(f"{y}:Q", title=y_title, scale=scale,
                  axis=alt.Axis(format=y_format) if y_format else alt.Undefined)
    tip = [alt.Tooltip("ano:Q", title="Ano", format="d"),
           alt.Tooltip(f"{y}:Q", title=y_title, format=fmt)] + _tip_motivo(df)
    line = alt.Chart(d[~d["atipico"]]).mark_line(color=color, strokeWidth=2).encode(x=ANO_X, y=y_enc)
    legend = alt.Legend(**LEGEND_TOP) if _has_atip(df) else None
    points = alt.Chart(d).mark_point(size=50, strokeWidth=2).encode(
        x=ANO_X, y=y_enc, tooltip=tip,
        color=alt.Color("status:N", scale=alt.Scale(domain=STATUS, range=[color, ATIP]), legend=legend),
        fill=alt.condition(alt.datum.atipico, alt.value("transparent"), alt.value(color)))
    return (line + points).properties(height=280)


def multi_line(df, y, series, y_title, colors, fmt=".2f", y_format=None, domain=None):
    """df long: ano, series, y. colors: {series: hex} in fixed order."""
    color = alt.Color(f"{series}:N", title=None, scale=alt.Scale(domain=list(colors),
                                                                 range=list(colors.values())),
                      legend=alt.Legend(**LEGEND_TOP))
    scale = alt.Scale(domain=domain) if domain else alt.Undefined
    base = alt.Chart(df).encode(
        x=ANO_X, color=color,
        y=alt.Y(f"{y}:Q", title=y_title, scale=scale,
                axis=alt.Axis(format=y_format) if y_format else alt.Undefined))
    tip = [alt.Tooltip("ano:Q", title="Ano", format="d"), alt.Tooltip(f"{series}:N", title="Série"),
           alt.Tooltip(f"{y}:Q", title=y_title, format=fmt)]
    return (base.mark_line(strokeWidth=2)
            + base.mark_point(size=40, filled=True).encode(tooltip=tip)).properties(height=300)


def stacked_ano(df, y, cat, y_title, colors, normalize=False, fmt=",.0f"):
    """Stacked bars per year; df long: ano, cat, y (+ atipico/motivo to fade years)."""
    present = [c for c in colors if c in set(df[cat])]
    stack = "normalize" if normalize else "zero"
    d = _with_status(df)
    return alt.Chart(d).mark_bar(stroke="#F6F1E7", strokeWidth=1).encode(
        x=alt.X("ano:O", title="Ano do processo"),
        y=alt.Y(f"{y}:Q", title=y_title, stack=stack,
                axis=alt.Axis(format="%") if normalize else alt.Undefined),
        color=alt.Color(f"{cat}:N", title=None, sort=present,
                        scale=alt.Scale(domain=present, range=[colors[c] for c in present]),
                        legend=alt.Legend(**LEGEND_TOP, columns=4)),
        opacity=alt.condition(alt.datum.atipico, alt.value(FADED), alt.value(1.0)),
        order=alt.Order("ordem:Q"),
        tooltip=[alt.Tooltip("ano:O", title="Ano"), alt.Tooltip(f"{cat}:N", title="Categoria"),
                 alt.Tooltip(f"{y}:Q", title=y_title, format=fmt)] + _tip_motivo(df),
    ).transform_calculate(
        ordem=f"indexof({present!r}, datum['{cat}'])"
    ).properties(height=340)


# Streamlit's height="content" fits axes and legend into the chart height, so
# category charts size by row to keep every label visible.
def _rows_height(n, per_row=28, extra=60):
    return extra + per_row * max(n, 1)


def hbar(df, cat, value, title, fmt=",.0f", color=CAT[0], height=None):
    return alt.Chart(df).mark_bar(color=color, cornerRadiusTopRight=3, cornerRadiusBottomRight=3).encode(
        y=alt.Y(f"{cat}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=280)),
        x=alt.X(f"{value}:Q", title=title),
        tooltip=[alt.Tooltip(f"{cat}:N", title="Item"), alt.Tooltip(f"{value}:Q", title=title, format=fmt)],
    ).properties(height=height or _rows_height(len(df), per_row=24))


def box_log(df, cat, value, title, colors):
    """Horizontal boxes (labels on the y axis never collide)."""
    present = [c for c in colors if c in set(df[cat])]
    return alt.Chart(df).mark_boxplot(size=18, extent=1.5, median={"color": "white"}).encode(
        y=alt.Y(f"{cat}:N", sort=present, title=None, axis=alt.Axis(labelLimit=160)),
        x=alt.X(f"{value}:Q", title=title, scale=alt.Scale(type="log")),
        color=alt.Color(f"{cat}:N", legend=None,
                        scale=alt.Scale(domain=present, range=[colors[c] for c in present])),
    ).properties(height=_rows_height(len(present), per_row=34))


def heatmap(df, x, y, value, title, fmt=",.0f", x_sort=None, y_sort=None, pct=False):
    d = _with_status(df)
    base = alt.Chart(d).encode(
        x=alt.X(f"{x}:O", title=None, sort=x_sort),
        y=alt.Y(f"{y}:N", title=None, sort=y_sort, axis=alt.Axis(labelLimit=220)))
    rect = base.mark_rect(stroke="#F6F1E7", strokeWidth=1).encode(
        color=alt.Color(f"{value}:Q", title=title, scale=alt.Scale(range=SEQ),
                        legend=alt.Legend(format="%" if pct else fmt, orient="right")),
        opacity=alt.condition(alt.datum.atipico, alt.value(FADED), alt.value(1.0)),
        tooltip=[alt.Tooltip(f"{x}:O", title="Coluna"), alt.Tooltip(f"{y}:N", title="Linha"),
                 alt.Tooltip(f"{value}:Q", title=title, format=".0%" if pct else fmt)] + _tip_motivo(df))
    return rect.properties(height=_rows_height(d[y].nunique(), per_row=30, extra=90))


MAP_MODES = {"Pontos": "pontos", "Hexágonos: processos": "processos", "Hexágonos: área": "area"}

TOOLTIP_STYLE = {"backgroundColor": "#F6F1E7", "color": "#2B2A28", "fontFamily": "Lato, sans-serif",
                 "fontSize": "12px", "border": "1px solid #DDD2BC", "borderRadius": "4px"}


def mapa(df, modo):
    """Points coloured by 3 macro uses (+ gray), radius ~ sqrt(m²); or hexagon density."""
    pts = df.dropna(subset=["latitude", "longitude"]).copy()
    modo = MAP_MODES[modo]
    view = pdk.ViewState(latitude=-27.105, longitude=-48.61, zoom=12.3, pitch=40 if modo != "pontos" else 0)
    if modo == "pontos":
        pts["cor"] = pts["uso_macro"].map(MACRO_RGB)
        pts["raio"] = np.sqrt(pts["metragem_m2"].fillna(100)).clip(6, 80)
        pts["area_txt"] = pts["metragem_m2"].map(lambda v: "n/d" if pd.isna(v) else f"{v:,.0f} m²")
        layer = pdk.Layer("ScatterplotLayer", pts, get_position="[longitude, latitude]",
                          get_fill_color="cor", get_radius="raio", opacity=0.75, pickable=True,
                          stroked=True, get_line_color=[246, 241, 231], line_width_min_pixels=1)
        tooltip = {"html": "<b>{processo}</b><br/>{utilizacao}<br/>{area_txt}<br/>{bairro_nome}",
                   "style": TOOLTIP_STYLE}
    else:
        pts["peso"] = pts["metragem_m2"].fillna(0) if modo == "area" else 1
        layer = pdk.Layer("HexagonLayer", pts, get_position="[longitude, latitude]",
                          get_elevation_weight="peso", get_color_weight="peso",
                          elevation_aggregation="SUM", color_aggregation="SUM",
                          radius=150, elevation_scale=4 if modo == "processos" else 0.05,
                          extruded=True, pickable=True, coverage=0.9, color_range=SEQ_RGB)
        tooltip = {"html": "Soma: {elevationValue}", "style": TOOLTIP_STYLE}
    # pydeck defaults to a dark basemap; the light Carto style suits the cream page.
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, tooltip=tooltip,
                             map_style="light"),
                    width="stretch", height=520)
