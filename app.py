import asyncio
import streamlit as st
import pandas as pd

from scraper import buscar_anuncios_olx

MAX_ANUNCIOS = 3000  # limite seguro fixo (você pediu)
DEFAULT_PATH = "/celulares"  # Brasil todo


def run_async(coro):
    """
    Evita erro de event loop em alguns ambientes.
    """
    try:
        loop = asyncio.get_running_loop()
        # se já existe loop rodando, cria outro
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
    except RuntimeError:
        return asyncio.run(coro)


st.set_page_config(page_title="OLX Celulares Scraper", layout="wide")

st.title("OLX – Celulares e Smartphones (Brasil)")
st.caption("Busca com filtros e retorna resultados em uma planilha visual (tabela).")

with st.sidebar:
    st.header("Filtros (como na OLX)")

    # APP “zerado”: tudo começa vazio/sem seleção
    termo = st.text_input("Termo de busca (q)", value="", placeholder="Ex: iphone 15 pro max")

    col1, col2 = st.columns(2)
    with col1:
        preco_min = st.number_input("Preço mínimo (ps)", min_value=0, value=0, step=50)
    with col2:
        preco_max = st.number_input("Preço máximo (pe)", min_value=0, value=0, step=50)

    st.divider()
    st.subheader("Atalhos de categoria (path)")

    # Você pode evoluir isso depois para refletir 100% os caminhos do PDF,
    # mas aqui mantém Brasil todo e permite Apple/usado-excelente etc.
    path = st.text_input(
        "Path da OLX (categoria)",
        value=DEFAULT_PATH,
        help='Ex: /celulares/apple/usado-excelente (como no seu link)',
    )

    st.divider()
    st.subheader("Parâmetros extras (do seu link)")

    # do seu exemplo:
    # opst=2 (OLX Pay?) e elbh=1/2 (Entrega)
    opst = st.multiselect("opst", options=[1, 2, 3, 4], default=[])
    elbh = st.multiselect("elbh", options=[1, 2, 3], default=[])

    st.caption("Dica: mantenha o resultado <= 3.000 anúncios para evitar bloqueio e lentidão.")

    buscar = st.button("Buscar anúncios", type="primary")

st.write("")

if buscar:
    params = {}

    if termo.strip():
        params["q"] = termo.strip()

    # só aplica preço se preenchido
    if preco_min and preco_min > 0:
        params["ps"] = int(preco_min)
    if preco_max and preco_max > 0:
        params["pe"] = int(preco_max)

    if opst:
        params["opst"] = opst
    if elbh:
        params["elbh"] = elbh

    st.info(f"Coletando anúncios (limite de segurança: {MAX_ANUNCIOS}). Pode demorar um pouco.")

    with st.spinner("Buscando e abrindo anúncios para extrair descrição…"):
        df = run_async(
            buscar_anuncios_olx(
                path=path.strip() if path.strip() else DEFAULT_PATH,
                params=params,
                max_anuncios=MAX_ANUNCIOS,
            )
        )

    if df is None or df.empty:
        st.warning("Nenhum anúncio encontrado (ou a OLX não carregou listagens). Tente ajustar filtros.")
    else:
        st.success(f"Anúncios coletados: {len(df)}")
        st.dataframe(df, use_container_width=True, hide_index=True)
