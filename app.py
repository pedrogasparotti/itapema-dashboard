"""EDA: alvarás de construção de Itapema/SC (1994 a 2026).

Run:  streamlit run eda_app/app.py
Deps: see eda_app/requirements-eda.txt (antd-components / extras optional)
Deep link to a chapter: ?cap=<slug>, e.g. ?cap=uso-do-solo
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
st.set_page_config(page_title="EDA Alvarás Itapema", page_icon="🏙️", layout="wide")

import ui  # noqa: E402
from data import (TOTAL, USO_GRUPOS, apply_filters, atypical_set, fmt_int,  # noqa: E402
                  fmt_years, load)
from sections import (p0_visao_geral, p1_dados, p2_tempo, p3_uso, p4_espaco,  # noqa: E402
                      p5_agentes, p6_explorar)

CAPITULOS = [  # (label, bootstrap icon, url slug, module)
    ("Visão geral", "house", "visao-geral", p0_visao_geral),
    ("Dados e qualidade", "clipboard-check", "dados", p1_dados),
    ("Dinâmica temporal", "graph-up", "tempo", p2_tempo),
    ("Uso do solo", "buildings", "uso-do-solo", p3_uso),
    ("Espaço", "geo-alt", "espaco", p4_espaco),
    ("Agentes e concentração", "people", "agentes", p5_agentes),
    ("Explorar dados", "table", "explorar", p6_explorar),
]
SLUGS = [slug for _, _, slug, _ in CAPITULOS]

df_all = load()
ui.inject_css()
anos_min, anos_max = int(df_all["ano"].min()), int(df_all["ano"].max())
atip_cont, atip_area = atypical_set("contagem"), atypical_set("area")
cap_param = st.query_params.get("cap")

with st.sidebar:
    st.markdown("### Alvarás de construção\nItapema/SC")
    escolha = ui.menu([(n, i) for n, i, _, _ in CAPITULOS], key="menu",
                      index=SLUGS.index(cap_param) if cap_param in SLUGS else 0)
    st.divider()
    st.markdown("**Filtros**")
    anos = st.slider("Ano do processo", anos_min, anos_max, (anos_min, anos_max))
    ocultar = st.toggle("Ocultar anos atípicos", value=False,
                        help="Anos com menos de 30 processos (ou 30 com área, nos gráficos de área) "
                             "e o ano parcial de 2026. Vale para os gráficos por ano e por período.")
    st.caption(f"Atípicos: {fmt_years(atip_cont)}; nos gráficos de área também "
               f"{fmt_years(atip_area - atip_cont)}.")
    bairros_opts = df_all["bairro_macro"].value_counts().index.tolist()
    bairros = st.multiselect("Bairro", bairros_opts, placeholder="Todos os bairros")
    usos = ui.chips("Uso (utilização)", USO_GRUPOS, key="usos")
    so_def = st.toggle("Somente deferidos", value=False, help="Decisão registrada no processo.")

df = apply_filters(df_all, anos, bairros, usos, so_def)
with st.sidebar:
    st.caption(f"**{fmt_int(len(df))}** de {fmt_int(TOTAL)} processos selecionados")

label, _, slug, modulo = next(c for c in CAPITULOS if c[0] == escolha)
st.query_params["cap"] = slug
st.title(label)
if df.empty and modulo is not p0_visao_geral:
    ui.empty()
else:
    modulo.render(df, df_all, anos, ocultar)
