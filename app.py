import asyncio
import streamlit as st

from scraper import buscar_anuncios_olx

st.set_page_config(page_title="OLX Celulares Scraper", layout="wide")

st.title("OLX – Celulares e Smartphones (Scraper)")

with st.expander("Como funciona", expanded=False):
    st.write(
        "Você seleciona os filtros (iguais aos da OLX) e o app busca anúncios "
        "paginando automaticamente. Por segurança, há um limite de 3.000 anúncios."
    )

# -----------------------------
# APP “ZERADO” (sem pré-seleções)
# -----------------------------
# Path base igual à categoria que você está usando.
# Ex.: /celulares/apple/usado-excelente (marca + condição no path)
st.subheader("Filtros")

col1, col2, col3, col4 = st.columns(4)

with col1:
    termo = st.text_input("Termo de busca (q)", value="")

with col2:
    preco_min = st.number_input("Preço mínimo (ps)", min_value=0, value=0, step=50)

with col3:
    preco_max = st.number_input("Preço máximo (pe)", min_value=0, value=0, step=50)

with col4:
    ordenar = st.selectbox(
        "Ordenar por (opst)",
        options=[
            (None, "Padrão / Mais relevantes"),
            (2, "Mais recentes"),
            (3, "Menor preço"),
            (4, "Maior preço"),
        ],
        format_func=lambda x: x[1],
        index=0,
    )[0]

st.markdown("---")

# Anúncios com (do seu print): Garantia da OLX / Garantia + Entrega (elbh=1/2)
colA, colB, colC = st.columns(3)

with colA:
    garantia_olx = st.checkbox("Garantia da OLX (elbh=1)", value=False)

with colB:
    garantia_entrega = st.checkbox("Garantia + Entrega (elbh=2)", value=False)

with colC:
    st.caption("Dica: esses dois filtros aumentam a qualidade do resultado.")

# Por enquanto, mantendo o PATH fixo igual ao seu caso do print/link.
# Depois você pode transformar Marca/Condição em selects e montar o path dinamicamente.
path = "/celulares/apple/usado-excelente"

# Limite “seguro”
MAX_ANUNCIOS = 3000

buscar = st.button("Buscar anúncios", type="primary")

if buscar:
    # validação simples
    if preco_max and preco_min and preco_max < preco_min:
        st.error("Preço máximo (pe) não pode ser menor que o preço mínimo (ps).")
        st.stop()

    params = {}

    if termo.strip():
        params["q"] = termo.strip()

    if preco_min > 0:
        params["ps"] = int(preco_min)

    if preco_max > 0:
        params["pe"] = int(preco_max)

    if ordenar is not None:
        params["opst"] = ordenar

    elbh = []
    if garantia_olx:
        elbh.append(1)
    if garantia_entrega:
        elbh.append(2)
    if elbh:
        params["elbh"] = elbh  # vira elbh=1&elbh=2

    st.info(f"Buscando anúncios (até {MAX_ANUNCIOS})… Isso pode demorar.")

    with st.spinner("Coletando links e abrindo anúncios para extrair detalhes…"):
        df = asyncio.run(
            buscar_anuncios_olx(
                path=path,
                params=params,
                max_anuncios=MAX_ANUNCIOS,
                concorrencia=6,
            )
        )

    st.success(f"Pronto! Encontrei {len(df)} anúncios.")

    # Visual (sem CSV)
    st.dataframe(df, use_container_width=True, hide_index=True)
