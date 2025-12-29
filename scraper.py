import re
import pandas as pd
from playwright.async_api import async_playwright

OLX_BASE = "https://www.olx.com.br/celulares"
SYSTEM_CHROMIUM = "/usr/bin/chromium"  # chromium instalado via packages.txt

def _preco_num(preco_txt: str):
    if not preco_txt:
        return None
    digits = re.sub(r"[^\d]", "", preco_txt)
    return int(digits) if digits else None


async def buscar_olx_com_filtros(
    termo: str,
    anuncios_com: list[str],
    marca: str | None,
    modelo: str,
    condicoes: list[str],
    baterias: list[str],
    preco_min: int | None,
    preco_max: int | None,
    headless: bool = True,
    limite_anuncios: int = 3000,
):
    """
    Retorna (df, info)
    info = {"atingiu_limite": bool, "limite": int}

    Obs: ainda está na versão simples (1ª página). Depois a gente faz paginação + clique 1:1.
    """

    params = []
    if termo:
        params.append(f"q={termo}")
    if preco_min is not None and preco_min > 0:
        params.append(f"ps={preco_min}")
    if preco_max is not None and preco_max > 0:
        params.append(f"pe={preco_max}")

    url = OLX_BASE + ("?" + "&".join(params) if params else "")

    resultados = []
    atingiu_limite = False

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,  # sempre headless no Streamlit Cloud
            executable_path=SYSTEM_CHROMIUM,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )

        context = await browser.new_context(locale="pt-BR")
        page = await context.new_page()

        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)

        cards = await page.query_selector_all('section[data-testid="listing-item-wrapper"]')

        for el in cards:
            if len(resultados) >= limite_anuncios:
                atingiu_limite = True
                break

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
                    "Descrição": "",
                }
            )

        await context.close()
        await browser.close()

    df = pd.DataFrame(resultados)
    info = {"atingiu_limite": atingiu_limite, "limite": limite_anuncios}
    return df, info
