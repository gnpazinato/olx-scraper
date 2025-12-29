import asyncio
import re
from urllib.parse import urlencode

import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


OLX_BASE = "https://www.olx.com.br"


def build_search_url(path: str, params: dict) -> str:
    """
    path exemplo: "/celulares/apple/usado-excelente"
    params exemplo: {"ps": 2000, "pe": 4500, "q": "iphone 15 pro max", "opst": 2, "elbh": [1,2], "o": 1}
    """
    # remove None/"" e mantém listas (ex.: elbh=[1,2])
    clean = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        clean[k] = v

    qs = urlencode(clean, doseq=True)
    return f"{OLX_BASE}{path}?{qs}" if qs else f"{OLX_BASE}{path}"


async def _extract_links_from_results_page(page) -> list[str]:
    """
    Extrai links de anúncios da página de resultados.
    Heurística: URLs terminando com um ID numérico grande (ex.: ...-1464735998).
    """
    hrefs = await page.eval_on_selector_all(
        "a[href]",
        "els => els.map(e => e.href).filter(Boolean)"
    )

    ad_links = []
    pattern = re.compile(r"^https://[a-z]{2}\.olx\.com\.br/.+-\d{7,}$")
    for h in hrefs:
        if pattern.match(h):
            ad_links.append(h)

    # remove duplicados preservando ordem
    seen = set()
    unique = []
    for h in ad_links:
        if h not in seen:
            seen.add(h)
            unique.append(h)
    return unique


async def _extract_ad_details(context, url: str, sem: asyncio.Semaphore) -> dict:
    """
    Abre o anúncio e extrai:
    - Título
    - Preço
    - Localização (texto)
    - Descrição
    """
    async with sem:
        p = await context.new_page()
        try:
            await p.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Título (na página do anúncio aparece como texto grande, normalmente h1)
            title = ""
            h1 = await p.query_selector("h1")
            if h1:
                title = (await h1.inner_text()).strip()

            # Preço (muitas vezes aparece como "R$ X.XXX" em um bloco destacado)
            # Pegamos o primeiro texto que pareça preço.
            body_text = await p.text_content("body")
            price = ""
            if body_text:
                m = re.search(r"R\$\s?[\d\.\u00A0]+", body_text)
                if m:
                    price = m.group(0).replace("\u00A0", " ").strip()

            # Descrição: em alguns layouts existe data-testid, mas vamos usar fallback
            desc = ""
            desc_el = await p.query_selector('[data-testid="ad-description"]')
            if desc_el:
                desc = (await desc_el.inner_text()).strip()
            else:
                # fallback: tenta pegar o primeiro parágrafo grande depois do título
                # (heurística simples para não ficar vazio)
                ps = await p.query_selector_all("p")
                if ps:
                    cand = []
                    for el in ps[:8]:
                        t = (await el.inner_text()).strip()
                        if len(t) >= 40:
                            cand.append(t)
                    desc = cand[0] if cand else ""

            desc = desc.replace("\n", " ").strip()

            # Localização: aparece como texto próximo do bloco "Localização"
            location = ""
            if body_text:
                # pega uma janela de texto ao redor da palavra "Localização"
                idx = body_text.find("Localização")
                if idx != -1:
                    snippet = body_text[idx: idx + 250]
                    location = " ".join(snippet.split()).replace("Localização", "").strip()

            return {
                "Título": title or "",
                "Preço": price or "",
                "Localização": location or "",
                "Descrição": desc or "",
                "Link": url,
            }

        except PlaywrightTimeoutError:
            return {"Título": "", "Preço": "", "Localização": "", "Descrição": "", "Link": url}
        except Exception:
            return {"Título": "", "Preço": "", "Localização": "", "Descrição": "", "Link": url}
        finally:
            await p.close()


async def buscar_anuncios_olx(
    *,
    path: str,
    params: dict,
    max_anuncios: int = 3000,
    concorrencia: int = 6,
    pausa_entre_paginas_s: float = 0.8,
) -> pd.DataFrame:
    """
    - path: caminho da categoria (ex.: "/celulares/apple/usado-excelente")
    - params: dict de querystring (ex.: {"ps": 2000, "pe": 4500, "q": "iphone 15 pro max", "elbh":[1,2], "opst":2})
    - max_anuncios: limite de segurança
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="pt-BR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
        )
        page = await context.new_page()

        links = []
        pagina = 1

        try:
            while len(links) < max_anuncios:
                params_pagina = dict(params)
                params_pagina["o"] = pagina  # paginação (o=1, o=2, ...)
                url = build_search_url(path, params_pagina)

                await page.goto(url, wait_until="domcontentloaded", timeout=60000)

                novos = await _extract_links_from_results_page(page)
                # se não achou nada novo, para
                before = len(links)
                for u in novos:
                    if u not in links:
                        links.append(u)
                        if len(links) >= max_anuncios:
                            break

                if len(links) == before:
                    break

                pagina += 1
                await asyncio.sleep(pausa_entre_paginas_s)

            # agora coleta detalhes (concorrência controlada)
            sem = asyncio.Semaphore(concorrencia)
            tasks = [_extract_ad_details(context, u, sem) for u in links]
            rows = await asyncio.gather(*tasks)

            df = pd.DataFrame(rows)

            # limpa duplicados e linhas vazias demais
            df = df.drop_duplicates(subset=["Link"])
            return df

        finally:
            await context.close()
            await browser.close()
