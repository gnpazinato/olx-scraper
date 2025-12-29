import streamlit as st
import asyncio
from scraper import buscar_olx_com_filtros

st.set_page_config(page_title="OLX - Celulares (Planilha)", layout="wide")
st.title("OLX Celulares e Smartphones — Planilha")

with st.sidebar:
    st.header("Filtros (igual OLX)")

    anuncios_com = st.multiselect(
        "Anúncios com",
        ["Garantia da OLX", "Garantia + Entrega"],
        default=[],
    )

    termo = st.text_input("Buscar por termo", value="")

    marca = st.selectbox("Marca", ["(selecione)","APPLE"], index=0)
    modelo = st.selectbox("Modelo", ["Todos os modelos"], index=0)

    st.subheader("Condição")
    condicoes = []
    if st.checkbox("Novo", value=False): condicoes.append("Novo")
    if st.checkbox("Usado - Excelente", value=False): condicoes.append("Usado - Excelente")
    if st.checkbox("Usado - Bom", value=False): condicoes.append("Usado - Bom")
    if st.checkbox("Recondicionado", value=False): condicoes.append("Recondicionado")
    if st.checkbox("Com defeito", value=False): condicoes.append("Com defeito")

    st.subheader("Saúde da bateria")
    baterias = []
    if st.checkbox("Perfeita (95% até 100%)", value=False): baterias.append("Perfeita")
    if st.checkbox("Boa (80% até 94%)", value=False): baterias.append("Boa")
    if st.checkbox("OK (60% até 79%)", value=False): baterias.append("OK")
    if st.checkbox("Ruim (40% até 59%)", value=False): baterias.append("Ruim")
    if st.checkbox("Muito Ruim (abaixo de 39%)", value=False): baterias.append("Muito Ruim")

    st.subheader("Preço")
    preco_min = st.number_input("Preço mínimo", min_value=0, value=0, step=50)
    preco_max = st.number_input("Preço máximo", min_value=0, value=0, step=50)

    # mantém isso como config técnica (pode esconder depois), mas não como “filtro”
    headless = st.checkbox("Modo headless (recomendado no Streamlit Cloud)", value=True)

# Botão só roda se tiver pelo menos algo selecionado
if st.button("Buscar", type="primary"):
    if marca == "(selecione)" and termo.strip() == "" and preco_min == 0 and preco_max == 0 \
       and not anuncios_com and not condicoes and not baterias:
        st.warning("Selecione ao menos um filtro (ou termo) para buscar.")
    else:
        with st.spinner("Aplicando filtros na OLX e coletando anúncios..."):
            df = asyncio.run(
                buscar_olx_com_filtros(
                    termo=termo.strip(),
                    anuncios_com=anuncios_com,
                    marca=None if marca == "(selecione)" else marca,
                    modelo=modelo,
                    condicoes=condicoes,
                    baterias=baterias,
                    preco_min=int(preco_min) if preco_min else None,
                    preco_max=int(preco_max) if preco_max else None,
                    headless=headless,
                )
            )

        st.success(f"Concluído: {len(df)} anúncios")
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Link": st.column_config.LinkColumn("Link", display_text="Abrir"),
                "PreçoNum": st.column_config.NumberColumn("PreçoNum"),
                "Título": st.column_config.TextColumn("Título", width="large"),
                "Descrição": st.column_config.TextColumn("Descrição", width="large"),
            },
        )
else:
    st.info("Selecione filtros na barra lateral e clique em **Buscar**.")
