import asyncio
from urllib.parse import urlencode, urljoin

import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def build_olx_url(path: str, params: dict) -> str:
    """
    path exemplo: "/celulares/apple/usado-excelente"
    params exemplo: {"q":"iphone 15 pro max", "ps":2000, "pe":4500, "opst":[2], "elbh":[1,2]}
    """
    base = "https://www.olx.com.br"
    if not path.startswith("/"):
        path = "/" + path

    # remove None/"" e permite listas (doseq)
    clean = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, str) and v.strip() == "":
            continue
        clean[k] = v

    qs = urlencode(clean, doseq=True)
    return urljoin(base, path) + (("?" + qs) if qs else "")


async def buscar_anuncios_olx(
    path: str,
    params: dict,
    max_anuncios: int = 3000,
    delay_s: float = 0.8,
) -> pd.DataFrame:
    """
    - Abre a busca, pagina (o=1..n) e coleta links/títulos/preços.
    - Depois entra em cada anúncio para extrair descrição.
    - max_anuncios = limite de segurança (você pediu 3.000).
    """

    resultados = []
    vistos = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="pt-BR",
            user_agent=DEFAULT_UA,
            viewport={"width": 1365, "height": 768},
        )
        page = await context.new_page()

        # paginação via "o="
        pagina = 1
        while True:
            params_paginados = dict(params)
            params_paginados["o"] = pagina

            url = build_olx_url(path, params_paginados)
            await page.goto(url, wait_until="domcontentloaded")

            # Tenta esperar algum item aparecer
            try:
                await page.wait_for_selector('section[data-testid="listing-item-wrapper"]', timeout=8000)
            except PlaywrightTimeoutError:
                # Pode ser bloqueio/antibot ou busca sem resultados
                html = (await page.content()).lower()
                if "robô" in html or "verificação" in html or "captcha" in html:
                    # sinaliza no DF para você enxergar na UI
                    await browser.close()
                    return pd.DataFrame([{
                        "Título": "BLOQUEIO/VERIFICAÇÃO DA OLX",
                        "Preço": "",
                        "Link": url,
                        "Descrição": "A OLX pode ter bloqueado a automação. Tente reduzir filtros/volume e rodar de novo."
                    }])
                break

            cards = await page.query_selector_all('section[data-testid="listing-item-wrapper"]')
            if not cards:
                break

            # Coleta preliminar
            coletados_essa_pagina = 0
            for el in cards:
                link_el = await el.query_selector('a[data-testid="item-direct-link"]')
                titulo_el = await el.query_selector("h2")
                preco_el = await el.query_selector('span[aria-label^="Preço"]')

                if not link_el:
                    continue

                link = await link_el.get_attribute("href")
                if not link:
                    continue

                # link pode vir relativo
                if link.startswith("/"):
                    link = "https://www.olx.com.br" + link

                if link in vistos:
                    continue

                titulo = (await titulo_el.inner_text()) if titulo_el else ""
                preco = (await preco_el.inner_text()) if preco_el else ""

                vistos.add(link)
                resultados.append({"Título": titulo.strip(), "Preço": preco.strip(), "Link": link})
                coletados_essa_pagina += 1

                if len(resultados) >= max_anuncios:
                    break

            # Se não coletou nada novo nesta página, para
            if coletados_essa_pagina == 0:
                break

            if len(resultados) >= max_anuncios:
                break

            pagina += 1
            await asyncio.sleep(0.4)

        # Agora entra em cada anúncio e pega descrição
        finais = []
        for i, item in enumerate(resultados, start=1):
            if i > max_anuncios:
                break
            try:
                await page.goto(item["Link"], wait_until="domcontentloaded")
                # descrição (padrão comum)
                desc_el = await page.query_selector('span[data-testid="ad-description"]')
                descricao = await desc_el.inner_text() if desc_el else ""
                item["Descrição"] = " ".join(descricao.split())
                finais.append(item)
                await asyncio.sleep(delay_s)
            except Exception:
                # não mata a coleta
                continue

        await browser.close()
        return pd.DataFrame(finais)
