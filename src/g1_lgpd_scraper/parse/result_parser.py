"""Parser central (BeautifulSoup) dos resultados de busca do G1.

Seletores centralizados e versionados, ver docs/adr/0002-selector-strategy-and-versioning.md.
"""

import logging
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from g1_lgpd_scraper.models import RawCard

logger = logging.getLogger("g1_lgpd_scraper.parse")

SELECTORS_V1 = {
    "results_container": ".results__content.all-search-results",
    "card": "li.widget--info",
    "title": ".widget--info__title",
    "summary": ".widget--info__description",
    "published_at": ".widget--info__meta",
    "link": "a[href]",
}

PAGE_SIZE = 10


def _extract_canonical_url(href: str) -> str | None:
    """Extrai a URL real da materia de dentro do link de tracking measures.globo.com.

    Se o href nao for um redirecionamento de tracking, devolve o proprio href como fallback.
    """
    if not href:
        return None
    query = parse_qs(urlparse(href).query)
    encoded = query.get("u", [None])[0]
    if encoded:
        return encoded
    return href


def parse_search_results(html: str, page_size: int = PAGE_SIZE) -> list[RawCard]:
    """Extrai os cards de resultado do HTML renderizado pelo browser headless.
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(SELECTORS_V1["card"])
    results: list[RawCard] = []

    for index, card in enumerate(cards):
        try:
            link = card.select_one(SELECTORS_V1["link"])
            url = _extract_canonical_url(link.get("href")) if link else None

            title_el = card.select_one(SELECTORS_V1["title"])
            title = title_el.get_text(strip=True) if title_el else None
            if title is None:
                logger.warning("card sem title (url=%s)", url)

            summary_el = card.select_one(SELECTORS_V1["summary"])
            summary = summary_el.get_text(strip=True) if summary_el else None
            if summary is None:
                logger.warning("card sem summary (url=%s)", url)

            meta_el = card.select_one(SELECTORS_V1["published_at"])
            published_at_raw = meta_el.get_text(strip=True) if meta_el else None
            if published_at_raw is None:
                logger.warning("card sem published_at (url=%s)", url)

            if not url:
                logger.warning("card %d sem URL extraivel, pulando", index)
                continue

            page_number = (index // page_size) + 1
            results.append(
                RawCard(
                    title=title,
                    url=url,
                    summary=summary,
                    published_at_raw=published_at_raw,
                    page_number=page_number,
                )
            )
        except Exception:
            logger.warning("falha ao processar card %d, pulando", index, exc_info=True)
            continue

    return results
