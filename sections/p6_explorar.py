"""Cap. 6: free exploration and download."""

import streamlit as st

import ui
from data import fmt_int

COLUNAS = {
    "processo": "Número do processo (NNN/AAAA)",
    "ano": "Ano do número do processo",
    "requerente": "Código e nome do requerente",
    "bairro_macro": "Bairro, sem código; códigos homônimos agregados",
    "loteamento_nome": "Loteamento",
    "logradouro_numero": "Logradouro e número, como no sistema",
    "zona": "Zona (ZR-1/2/3, ZC) quando registrada",
    "metragem": "Área original, em texto",
    "metragem_m2": "Área numérica (m²); nula quando vazia ou 0,00",
    "utilizacao": "Utilização: classe codificada, preenchida no refino quando inequívoca",
    "utilizacao_fonte": "Origem da utilização",
    "uso_grupo": "Agrupamento de uso usado nos gráficos",
    "deferido_processo": "Decisão do processo: deferido (SIM/NÃO)",
    "data_decisao_processo": "Data da decisão do processo",
    "deferido": "Análise do requerimento (vazia desde 2017)",
    "tipo_requerente": "PJ ou PF, por palavras do nome",
    "latitude": "Latitude (WGS84)",
    "longitude": "Longitude (WGS84)",
    "geocode_precision": "Precisão da geocodificação",
}


def render(df, df_all, anos, ocultar):
    filtrado = ui.explorer(df[list(COLUNAS)])
    st.dataframe(filtrado, hide_index=True, width="stretch", height=480,
                 column_config={"ano": st.column_config.NumberColumn(format="%d"),
                                "metragem_m2": st.column_config.NumberColumn("metragem_m2", format="%.2f")})
    st.download_button(f"Baixar {fmt_int(len(filtrado))} linhas (CSV)",
                       filtrado.to_csv(index=False).encode("utf-8-sig"),
                       file_name="alvaras_itapema_filtrado.csv", mime="text/csv")
    with st.expander("Dicionário de colunas"):
        st.table({"coluna": list(COLUNAS), "descrição": list(COLUNAS.values())})
