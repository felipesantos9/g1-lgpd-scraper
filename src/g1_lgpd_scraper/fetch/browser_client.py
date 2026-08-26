"""Caminho de coleta (ADR 0001)

Comportamento de paginacao confirmado com Playwright real -- ver
docs/diagnosis.md, Evidencia 3: nao existe URL de pagina; "pagina N" e
implementada como N-1 cliques sucessivos no botao ".pagination__load-more",
que faz append de +10 itens na mesma lista, sem navegar.

Confirmado tambem que buscas sem nenhum resultado real renderizam uma
estrutura distinta (".search-not-found__root", com o texto "Nenhum resultado
encontrado."), em vez do container de resultados ficar vazio -- isso permite
distinguir "zero resultados de verdade" de "algo quebrou" (drift de seletor,
falha de navegacao), ver docs/adr/0005-error-handling-and-retries.md.
"""

import logging
import time
from dataclasses import dataclass

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger("g1_lgpd_scraper.fetch.browser")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

LOAD_MORE_SELECTOR = ".pagination__load-more"
RESULTS_ITEM_SELECTOR = ".results__list li"
NOT_FOUND_SELECTOR = ".search-not-found__root"


class BrowserFetchError(Exception):
    """Levantada quando a coleta headless falha (browser ausente, crash, timeout,
    ou nem resultados nem a mensagem de "nao encontrado" aparecem -- sinal de
    que a estrutura da pagina mudou, nao de zero resultados legitimos)."""


@dataclass
class PageLoadResult:
    """Resultado de carregar a pagina de busca.

    genuinely_empty=True significa que o G1 confirmou, via
    ".search-not-found__root", que a busca nao tem resultados -- nao e uma
    falha. Se nem resultados nem essa mensagem aparecerem, isso e tratado
    como falha (BrowserFetchError), nao como "genuinely_empty".
    """

    html: str
    genuinely_empty: bool


class BrowserSession:
    """Sessao de uma unica pagina do navegador, reaproveitada entre "paginas" logicas.

    Uso: with BrowserSession() as session: result = session.load_up_to_page(url, n)
    """

    def __init__(self, timeout_ms: int = 30_000, max_retries: int = 3, delay_seconds: float = 1.0):
        self._timeout_ms = timeout_ms
        self._max_retries = max_retries
        self._delay_seconds = delay_seconds
        self._playwright = None
        self._browser = None
        self._page = None

    def __enter__(self) -> "BrowserSession":
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            self._page = self._browser.new_page(user_agent=USER_AGENT)
        except Exception as exc:
            self.close()
            raise BrowserFetchError(
                "falha ao iniciar o Chromium headless. "
                "Verifique se 'playwright install chromium' foi executado."
            ) from exc
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        for closer in (self._browser, self._playwright):
            if closer is not None:
                try:
                    closer.close() if hasattr(closer, "close") else closer.stop()
                except Exception:
                    logger.debug("erro ao encerrar recurso do browser", exc_info=True)
        self._playwright = None
        self._browser = None
        self._page = None

    def _navigate(self, url: str) -> None:
        """Carrega a URL e espera o primeiro lote de resultados OU a mensagem
        de "nao encontrado" aparecer, com retry/backoff para falhas
        transitorias (timeout de rede, carregamento incompleto) -- ver
        docs/adr/0005-error-handling-and-retries.md."""

        wait_selector = f"{RESULTS_ITEM_SELECTOR}, {NOT_FOUND_SELECTOR}"

        @retry(
            retry=retry_if_exception_type(Exception),
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True,
        )
        def _attempt() -> None:
            self._page.goto(url, wait_until="domcontentloaded", timeout=self._timeout_ms)
            self._page.wait_for_selector(wait_selector, timeout=self._timeout_ms)

        try:
            _attempt()
        except Exception as exc:
            raise BrowserFetchError(
                f"falha ao carregar {url} no browser headless apos {self._max_retries} tentativas "
                f"(nem resultados nem mensagem de 'nao encontrado' apareceram): {exc}"
            ) from exc

    def load_up_to_page(self, url: str, target_page: int) -> PageLoadResult:
        """Carrega a URL e clica em "Veja mais" (target_page - 1) vezes.

        Se a busca genuinamente nao tiver resultados (".search-not-found__root"
        presente), pula direto para o retorno -- nao ha botao de carregar mais
        nem itens para contar nesse caso. Caso contrario, clica em "Veja mais"
        ate target_page ou ate o botao desaparecer/parar de trazer itens novos
        (fim real dos resultados) -- quem chama detecta isso comparando a
        contagem de itens antes/depois.
        """
        self._navigate(url)

        if self._page.locator(NOT_FOUND_SELECTOR).count() > 0:
            logger.info("busca sem resultados reais para esta query (confirmado por '%s')", NOT_FOUND_SELECTOR)
            return PageLoadResult(html=self._page.content(), genuinely_empty=True)

        clicks_needed = max(target_page - 1, 0)
        for click_number in range(clicks_needed):
            button = self._page.locator(LOAD_MORE_SELECTOR)
            if button.count() == 0:
                logger.info(
                    "botao 'Veja mais' nao encontrado apos %d cliques -- fim real dos resultados",
                    click_number,
                )
                break
            time.sleep(self._delay_seconds)
            before = self._page.locator(RESULTS_ITEM_SELECTOR).count()
            button.first.click()
            try:
                self._page.wait_for_function(
                    "([sel, count]) => document.querySelectorAll(sel).length > count",
                    arg=[RESULTS_ITEM_SELECTOR, before],
                    timeout=self._timeout_ms,
                )
            except PlaywrightTimeoutError:
                logger.info("clique em 'Veja mais' nao trouxe itens novos -- fim real dos resultados")
                break

        return PageLoadResult(html=self._page.content(), genuinely_empty=False)
