"""Cap. 1: pipeline, data quality, atypical years."""

import pandas as pd
import streamlit as st

import charts
import ui
from data import N_MIN_ANO, atypical_years, fmt_pct, mark_years

CAMPOS = {
    "Área (metragem_m2)": lambda d: d["metragem_m2"].notna(),
    "Utilização original": lambda d: d["utilizacao_original"] != "",
    "Utilização após refino": lambda d: d["utilizacao"] != "",
    "Zona (ZR/ZC)": lambda d: d["zona"] != "",
    "Validade": lambda d: d["validade"] != "",
    "Pagamento": lambda d: d["pagamento"] != "",
    "Coordenadas": lambda d: d["latitude"].notna(),
}
FONTES = {"original": "Original do sistema", "zoneamento": "Texto em zoneamento",
          "observacao_processo": "Observação do processo",
          "observacao_requerimento": "Observação do requerimento",
          "ambiguo": "Ambíguo (vazio)", "sem_informacao": "Sem informação (vazio)"}
PRECISAO = {"street": "Rua + número", "street_nonum": "Rua", "loteamento": "Loteamento",
            "bairro": "Bairro", "none": "Não localizado"}


def render(df, df_all, anos, ocultar):
    ui.steps([("PDF", "1.723 páginas do Sistema Terra"),
              ("Extração", "1 linha por processo"),
              ("Geocodificação", "Nominatim/OSM"),
              ("Refino", "área, uso e ano"),
              ("EDA", "este aplicativo")], key="pipeline")

    ui.heading("Completude dos campos por ano")
    rows = [{"ano": ano, "campo": campo, "preenchido": fn(g).mean()}
            for ano, g in df.groupby("ano") for campo, fn in CAMPOS.items()]
    comp = mark_years(pd.DataFrame(rows), "contagem", ocultar)
    with ui.chart_box(comp, "completude"):
        charts.show(charts.heatmap(comp, "ano", "campo", "preenchido", "% preenchido",
                                   y_sort=list(CAMPOS), pct=True))

    early, late = df[df["ano"] < 2014], df[df["ano"] >= 2014]
    ui.findings([
        f"Utilização preenchida no sistema: **{fmt_pct((early['utilizacao_original'] != '').mean())}** "
        f"antes de 2014 e **{fmt_pct((late['utilizacao_original'] != '').mean())}** depois.",
        f"Com o refino, a utilização cobre **{fmt_pct((df['utilizacao'] != '').mean())}** da seleção.",
        f"Área informada em **{fmt_pct(df['metragem_m2'].notna().mean())}** dos processos.",
    ], key="dados")

    c1, c2 = st.columns(2)
    with c1:
        ui.heading("Origem da utilização")
        f = df["utilizacao_fonte"].map(FONTES).value_counts().rename_axis("fonte") \
            .reset_index(name="processos")
        with ui.chart_box(f, "fonte_utilizacao"):
            charts.show(charts.hbar(f, "fonte", "processos", "Processos"))
    with c2:
        ui.heading("Precisão da geocodificação")
        p = df["geocode_precision"].map(PRECISAO).value_counts().rename_axis("precisao") \
            .reset_index(name="processos")
        with ui.chart_box(p, "geocode"):
            charts.show(charts.hbar(p, "precisao", "processos", "Processos", color=charts.CAT[3]))

    ui.heading("Situação da área por ano")
    estado = pd.Series("Informada", index=df.index)
    estado[df["_flags_refino"].str.contains("metragem_zero")] = "0,00 tratada como nula"
    estado[df["metragem"].str.strip() == ""] = "Vazia"
    est = mark_years(df.assign(estado=estado).groupby(["ano", "estado"]).size()
                     .reset_index(name="processos"), "contagem", ocultar)
    cores = {"Informada": charts.CAT[0], "0,00 tratada como nula": charts.CAT[1], "Vazia": charts.GRAY}
    with ui.chart_box(est, "estado_area"):
        charts.show(charts.stacked_ano(est, "processos", "estado", "Processos", cores))

    ui.heading("Anos atípicos")
    a = atypical_years()
    a = a[(a["atip_contagem"] | a["atip_area"]) & a["ano"].between(*anos)]
    st.dataframe(pd.DataFrame({
        "Ano": a["ano"].astype(str), "Processos": a["processos"], "Com área": a["com_area"],
        "Gráficos de contagem": a["motivo_contagem"].replace("", "ok"),
        "Gráficos de área": a["motivo_area"].replace("", "ok")}),
        hide_index=True, width="stretch", height=35 * (len(a) + 1) + 3)
    ui.note("Notas de método",
            f"Um ano é atípico com menos de {N_MIN_ANO} processos (ou {N_MIN_ANO} com área, nos "
            "gráficos de área) ou quando é parcial; o valor anual dependeria de poucos registros. "
            "O uso foi preenchido só quando o texto era inequívoco (ver `refine_report_validation.txt`).")
