"""Orquestracao de paginacao.
"""

import logging

from g1_lgpd_scraper.config import ScraperConfig
from g1_lgpd_scraper.fetch.browser_client import BrowserFetchError, BrowserSession
from g1_lgpd_scraper.models import RawCard
from g1_lgpd_scraper.parse.result_parser import parse_search_results

logger = logging.getLogger("g1_lgpd_scraper.pagination")


def collect_raw_cards(config: ScraperConfig) -> list[RawCard]:
    """Coleta cards de resultado ate config.max_pages, via browser headless.

    Nunca levanta excecao para falhas localizadas, retorna o que conseguiu
    coletar e loga o motivo, distinguindo os dois casos:
    - lista vazia + log INFO: o G1 confirmou (".search-not-found__root") que
      nao ha resultados para a query.
    - lista vazia + log ERROR: a coleta falhou de fato (browser, timeout, ou
      nem resultados nem a mensagem de "nao encontrado" apareceram).
    """
    url = config.search_url()
    timeout_ms = int(config.request_timeout_seconds * 1000)

    try:
        with BrowserSession(
            timeout_ms=timeout_ms,
            max_retries=config.max_retries,
            delay_seconds=config.request_delay_seconds,
        ) as session:
            result = session.load_up_to_page(url, config.max_pages)
    except BrowserFetchError as exc:
        logger.error("coleta headless falhou: %s", exc)
        return []

    if result.genuinely_empty:
        logger.info(
            "busca por query=%r nao retornou nenhum resultado (confirmado pela pagina)",
            config.query,
        )
        return []

    cards = parse_search_results(result.html)
    if not cards:
        logger.error(
            "pagina carregou resultados mas nenhum card casou com os seletores atuais "
            "(max_pages=%d) -- possivel mudanca na estrutura do site",
            config.max_pages,
        )
        return []

    if config.start_page > 1:
        cards = [card for card in cards if card.page_number >= config.start_page]

    logger.info("coleta headless coletou %d cards (max_pages=%d)", len(cards), config.max_pages)
    return cards
