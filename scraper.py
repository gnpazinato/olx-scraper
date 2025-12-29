import re
import pandas as pd
from playwright.async_api import async_playwright

OLX_BASE = "https://www.olx.com.br/celulares"

def _preco_num(preco_txt: str):
    if not preco_txt:
        return None
    digits = re.sub(r"[^\d]", "", preco_txt)
    return int(digits) if digits else None

async def buscar_olx_com_filtros(
    termo: str,
    anuncios_com: list[str],
    marca: str,
    modelo: str,
    condicoes: list[str],
    baterias: list[str],
    preco_min: int,
    preco_max: int,
    max_anuncios: int = 60,
    headless: bool = True,
) -> pd.DataFrame:
    """
    Versão inicial: abre a OLX e faz a busca.
    Na próxima etapa: aplicar filtros via clique (UI 1:1 OLX).
    """
    url = f"{OLX_BASE}?q={termo}&ps={preco_min}&pe={preco_max}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(locale="pt-BR")
        page = await context.new_page()

        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)

        # coleta cards (primeira página)
        cards = await page.query_selector_all('section[data-testid="listing-item-wrapper"]')

        resultados = []
        for el in cards[:max_anuncios]:
            link_el = await el.query_selector('a[data-testid="item-direct-link"]')
            titulo_el = await el.query_selector("h2")
            preco_el = await el.query_selector('span[aria-label^="Preço"]')

            if not (link_el and titulo_el and preco_el):
                continue

            link = await link_el.get_attribute("href")
            if link and link.startswith("/"):
                link = "https://www.olx.com.br" + link

            titulo = (await titulo_el.inner_text()).strip()
            preco_txt = (await preco_el.inner_text()).strip()

            resultados.append(
                {
                    "Título": titulo,
                    "Preço": preco_txt,
                    "PreçoNum": _preco_num(preco_txt),
                    "Link": link,
                }
            )

        await context.close()
        await browser.close()

    return pd.DataFrame(resultados)
