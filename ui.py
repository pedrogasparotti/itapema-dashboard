"""UI building blocks: streamlit-antd-components / streamlit-extras when installed,
native Streamlit widgets otherwise, so the app runs either way.

antd widgets take no hard-coded colour: they inherit the theme's primary colour
(navy on the page, mustard in the navy sidebar; see .streamlit/config.toml).
"""

import contextlib

import streamlit as st

try:
    import streamlit_antd_components as sac
except ImportError:
    sac = None
try:
    from streamlit_extras.metric_cards import style_metric_cards
except ImportError:
    style_metric_cards = None
try:
    from streamlit_extras.chart_container import chart_container
except ImportError:
    chart_container = None
try:
    from streamlit_extras.dataframe_explorer import dataframe_explorer
except ImportError:
    dataframe_explorer = None
try:
    from streamlit_extras.stoggle import stoggle
except ImportError:
    stoggle = None

MUSTARD = "#E6B45E"
NAVY = "#263C75"
CARD_BG = "#FBF8F2"

# Findings boxes get the mustard accent; sidebar multiselect tags are mustard with
# white text by default (about 1.9:1), so their text turns navy.
CSS = f"""
<style>
[class*="st-key-achados"] {{border-left: 4px solid {MUSTARD} !important; background: {CARD_BG};}}
[data-testid="stSidebar"] [data-testid="stMultiSelectTagsContainer"] [aria-label="Selected values"] > *
  {{color: {NAVY} !important;}}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def menu(items, key, index=0):
    """items: [(label, bootstrap-icon)] -> selected label."""
    labels = [label for label, _ in items]
    if sac:
        return sac.menu([sac.MenuItem(label, icon=icon) for label, icon in items],
                        index=index, variant="left-bar", size="sm", key=key)
    return st.radio("Capítulos", labels, index=index, key=key, label_visibility="collapsed")


def chips(label, options, key):
    """Multi-select chips, all selected by default -> list of selected options."""
    if sac:
        sel = sac.chip([sac.ChipItem(label=o) for o in options], label=label,
                       index=list(range(len(options))), multiple=True, size="sm",
                       radius="md", variant="light", key=key)
        return list(sel or [])
    return st.pills(label, options, selection_mode="multi", default=options, key=key) or []


def segmented(options, key, label=None):
    if sac:
        return sac.segmented([sac.SegmentedItem(label=o) for o in options], label=label,
                             size="sm", key=key)
    val = st.segmented_control(label or "Métrica", options, default=options[0], key=key,
                               label_visibility="visible" if label else "collapsed")
    return val or options[0]


def alert(text, color="info"):
    if sac:
        sac.alert(label=text, color=color, variant="light", icon=True, size="sm")
    else:
        {"info": st.info, "warning": st.warning, "error": st.error,
         "success": st.success}[color](text)


def heading(label):
    """Section title. Native, so it renders in the theme's heading font (Garamond);
    antd widgets live in iframes that cannot load the web font."""
    st.markdown(f"#### {label}")


def steps(items, key):
    """items: [(title, description)]: a static pipeline diagram."""
    if sac:
        sac.steps([sac.StepsItem(title=t, description=d) for t, d in items],
                  index=len(items) - 1, size="sm", key=key)
        return
    cols = st.columns(len(items))
    for i, (col, (t, d)) in enumerate(zip(cols, items), 1):
        col.markdown(f"**{i}. {t}**  \n{d}")


def empty(msg="Nenhum processo para os filtros atuais."):
    if sac:
        sac.result(label=msg, status="warning")
    else:
        st.warning(msg)


def kpi_style():
    """Style st.metric tiles as cards (extras); returns kwargs for st.metric."""
    if style_metric_cards:
        style_metric_cards(background_color=CARD_BG, border_size_px=1, border_color="#E4DAC6",
                           border_radius_px=6, border_left_color=MUSTARD, box_shadow=False)
        return {}
    return {"border": True}


@contextlib.contextmanager
def chart_box(data, key):
    """Chart / Dados / Exportar tabs around a chart (extras), or chart + data expander."""
    if chart_container:
        with chart_container(data, export_formats=["CSV"]):
            yield
        return
    yield
    with st.expander("Ver dados do gráfico"):
        st.dataframe(data, hide_index=True, width="stretch")
        st.download_button("Baixar CSV", data.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"{key}.csv", mime="text/csv", key=f"dl_{key}")


def note(title, body):
    """Collapsible method note."""
    if stoggle:
        stoggle(title, body)
    else:
        with st.expander(title):
            st.markdown(body)


def explorer(df):
    if dataframe_explorer:
        return dataframe_explorer(df, case=False)
    q = st.text_input("Buscar em todas as colunas", placeholder="ex.: MEIA PRAIA, LTDA, 2019")
    if not q:
        return df
    mask = df.astype(str).apply(lambda c: c.str.contains(q, case=False, regex=False)).any(axis=1)
    return df[mask]


def findings(lines, key):
    """'Principais achados' box (mustard accent); lines come from the filtered data."""
    with st.container(border=True, key=f"achados_{key}"):
        st.markdown("##### Principais achados")
        st.markdown("\n".join(f"- {line}" for line in lines))
