import streamlit as st
import asyncio
from scraper import buscar_olx_com_filtros

st.set_page_config(page_title="OLX - Celulares (Planilha)", layout="wide")
st.title("OLX Celulares e Smartphones — Planilha")

# App sempre "zerado": nada pré-selecionado
with st.sidebar:
    st.header("Filtros (igual OLX)")

    anuncios_com = st.multiselect(
        "Anúncios com",
        ["Garantia da OLX", "Garantia + Entrega"],
        default=[],
    )

    termo = st.text_input("Buscar por termo", value="")

    # (por enquanto deixo só APPLE como exemplo; depois a gente puxa dinamicamente)
    marca = st.selectbox("Marca", ["(selecione)", "APPLE"], index=0)
    modelo = st.selectbox("Modelo", ["Todos os modelos"], index=0)

    st.subheader("Condição")
    condicoes = []
    if st.checkbox("Novo", value=False):
        condicoes.append("Novo")
    if st.checkbox("Usado - Excelente", value=False):
        condicoes.append("Usado - Excelente")
    if st.checkbox("Usado - Bom", value=False):
        condicoes.append("Usado - Bom")
    if st.checkbox("Recondicionado", value=False):
        condicoes.append("Recondicionado")
    if st.checkbox("Com defeito", value=False):
        condicoes.append("Com defeito")

    st.subheader("Saúde da bateria")
    baterias = []
    if st.checkbox("Perfeita (95% até 100%)", value=False):
        baterias.append("Perfeita")
    if st.checkbox("Boa (80% até 94%)", value=False):
        baterias.append("Boa")
    if st.checkbox("OK (60% até 79%)", value=False):
        baterias.append("OK")
    if st.checkbox("Ruim (40% até 59%)", value=False):
        baterias.append("Ruim")
    if st.checkbox("Muito Ruim (abaixo de 39%)", value=False):
        baterias.append("Muito Ruim")

    st.subheader("Preço")
    preco_min = st.number_input("Preço mínimo", min_value=0, value=0, step=50)
    preco_max = st.number_input("Preço máximo", min_value=0, value=0, step=50)

    st.caption("O app busca até 3.000 anúncios por pesquisa (limite de segurança).")

if st.button("Buscar", type="primary"):
    # validação leve: pelo menos algo deve estar setado
    if (
        marca == "(selecione)"
        and termo.strip() == ""
        and preco_min == 0
        and preco_max == 0
        and not anuncios_com
        and not condicoes
        and not baterias
    ):
        st.warning("Selecione ao menos um filtro (ou termo) para buscar.")
    else:
        with st.spinner("Aplicando filtros na OLX e coletando anúncios..."):
            df, info = asyncio.run(
                buscar_olx_com_filtros(
                    termo=termo.strip(),
                    anuncios_com=anuncios_com,
                    marca=None if marca == "(selecione)" else marca,
                    modelo=modelo,
                    condicoes=condicoes,
                    baterias=baterias,
                    preco_min=int(preco_min) if preco_min else None,
                    preco_max=int(preco_max) if preco_max else None,
                    headless=True,            # fixo (sem UI)
                    limite_anuncios=3000,     # fixo (sem UI)
                )
            )

        if info.get("atingiu_limite"):
            st.warning(
                f"A busca atingiu o limite de segurança de {info['limite']} anúncios. "
                "Refine os filtros na OLX para reduzir o total (ex.: ≤ 3.000) e tente novamente."
            )

        st.success(f"Coletados: {len(df)} anúncios")
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
