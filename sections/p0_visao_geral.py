"""Cap. 0: KPIs, context (chapters and metrics), caveats."""

import streamlit as st

import ui
from data import ANO_PARCIAL, N_MIN_ANO, fmt_int, fmt_pct

CAPITULOS = """
| Capítulo | O que responde |
|---|---|
| **Dados e qualidade** | De onde vêm os dados e quão completos são, ano a ano |
| **Dinâmica temporal** | Quanto se pediu para construir em cada ano, e de que tamanho |
| **Uso do solo** | O que se constrói e quanto da área nova é vertical |
| **Espaço** | Onde se constrói: mapa, bairros e zonas |
| **Agentes e concentração** | Quem constrói e se a área se concentra em poucos |
| **Explorar dados** | Tabela filtrável para consulta e download |
"""

METRICAS = f"""
| Métrica | Como é calculada | Para que serve |
|---|---|---|
| **Processos** | Um por número NNN/AAAA | Volume de pedidos |
| **Área requerida** | Soma da área informada (m²) | Tamanho do que se pretende construir |
| **Área média e mediana** | Por processo; a mediana ignora extremos | Ver se os projetos crescem |
| **Área vertical** | % da área em multifamiliar, multifamiliar + comercial e interesse social | Medir a verticalização |
| **Taxa de deferimento** | % de processos deferidos na decisão do processo | Acompanhar a aprovação |
| **Completude** | % de processos com o campo preenchido | Confiabilidade de cada campo por ano |
| **Participação da Meia Praia** | % da área anual localizada na Meia Praia | Concentração espacial |
| **Gini, decil superior, HHI** | Desigualdade da área entre requerentes (0 a 1) | Concentração entre agentes |
| **Pessoa jurídica** | % da área de nomes com LTDA, S/A, incorporadora… | Peso das empresas |
| **Requerentes distintos** | Códigos de requerente diferentes no ano | Diversidade de agentes |
| **Ano atípico** | Menos de {N_MIN_ANO} processos (ou {N_MIN_ANO} com área), ou ano parcial | Sinalizar pontos pouco confiáveis |
"""

FONTES = ("Fontes: [RBGFE/UFPE](https://periodicos.ufpe.br/revistas/index.php/rbgfe/article/download/263198/48738) · "
          "[PerCursos/UDESC](https://periodicos.udesc.br/index.php/percursos/article/download/17694/12209) · "
          "[Prefeitura de Itapema](https://itapema.sc.gov.br/wp-content/uploads/arquivos/downloads/66.pdf) · "
          "[UFSC](https://repositorio.ufsc.br/handle/123456789/269192) · "
          "[MDPI, 2019](https://www.mdpi.com/2071-1050/11/2/375/htm)")


def render(df, df_all, anos, ocultar):
    st.caption("Processos de alvará de construção do Relatório Analítico do Planejamento "
               "(Sistema Terra, Prefeitura de Itapema).")
    if df.empty:
        ui.empty()
        return

    area = df["metragem_m2"]
    top_bairro = df.groupby("bairro_macro")["metragem_m2"].sum().sort_values(ascending=False)
    vert_share = df.loc[df["vertical"], "metragem_m2"].sum() / area.sum() if area.sum() else float("nan")

    kw = ui.kpi_style()
    c = st.columns(5)
    c[0].metric("Processos", fmt_int(len(df)), **kw)
    c[1].metric("Área requerida (mil m²)", fmt_int(area.sum() / 1000), **kw)
    c[2].metric("Área mediana (m²)", fmt_int(area.median()) if area.notna().any() else "n/d", **kw)
    c[3].metric("Área vertical", fmt_pct(vert_share), **kw)
    c[4].metric("Bairro com mais área", top_bairro.index[0].title() if len(top_bairro) else "n/d", **kw)

    ui.heading("Contexto:")
    st.markdown("Itapema vive uma verticalização acelerada, concentrada na Meia Praia, com um Plano "
                "Diretor de 2002 em revisão. Este EDA usa os alvarás para medir esse processo no tempo, "
                "no espaço e entre os agentes.")
    st.caption(FONTES)
    left, right = st.columns([2, 3])
    with left:
        st.markdown("**Capítulos**")
        st.markdown(CAPITULOS)
    with right:
        st.markdown("**Métricas**")
        st.markdown(METRICAS)

    ui.heading("Leia antes")
    ui.alert(f"Ano é o do número do processo; {ANO_PARCIAL} é parcial.", "info")
    ui.alert("Área de 0,00 m² foi tratada como ausente.", "warning")
    ui.alert("Antes de 2014 o uso foi reconstruído a partir de texto livre.", "warning")
    ui.alert("Anos atípicos aparecem esmaecidos nos gráficos; oculte-os na barra lateral.", "info")
