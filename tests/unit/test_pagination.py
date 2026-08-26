import g1_lgpd_scraper.pagination as pagination_module
from g1_lgpd_scraper.config import ScraperConfig
from g1_lgpd_scraper.fetch.browser_client import BrowserFetchError, PageLoadResult

SINGLE_CARD_HTML = """
<div class="results__content all-search-results">
  <ul class="results__list">
    <li class="widget widget--info">
      <div class="widget--info__text-container">
        <a href="https://measures.globo.com/v1/click?u=https%3A%2F%2Fg1.globo.com%2Fok.ghtml">
          <div class="widget--info__title">Card unico</div>
        </a>
      </div>
    </li>
  </ul>
</div>
"""


class FakeBrowserSession:
    calls: list = []
    raise_error: bool = False
    genuinely_empty: bool = False

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def load_up_to_page(self, url, target_page):
        FakeBrowserSession.calls.append((url, target_page))
        if FakeBrowserSession.raise_error:
            raise BrowserFetchError("falha simulada")
        if FakeBrowserSession.genuinely_empty:
            return PageLoadResult(html="<div class='search-not-found__root'></div>", genuinely_empty=True)
        return PageLoadResult(html=SINGLE_CARD_HTML, genuinely_empty=False)


def setup_function():
    FakeBrowserSession.calls = []
    FakeBrowserSession.raise_error = False
    FakeBrowserSession.genuinely_empty = False


def test_collect_raw_cards_uses_browser_session_with_max_pages(monkeypatch):
    monkeypatch.setattr(pagination_module, "BrowserSession", FakeBrowserSession)

    config = ScraperConfig(max_pages=3)
    cards = pagination_module.collect_raw_cards(config)

    assert len(cards) == 1
    assert cards[0].title == "Card unico"
    assert FakeBrowserSession.calls == [(config.search_url(), 3)]


def test_collect_raw_cards_returns_empty_list_on_browser_failure(monkeypatch, caplog):
    FakeBrowserSession.raise_error = True
    monkeypatch.setattr(pagination_module, "BrowserSession", FakeBrowserSession)

    config = ScraperConfig(max_pages=1)
    with caplog.at_level("INFO", logger="g1_lgpd_scraper.pagination"):
        cards = pagination_module.collect_raw_cards(config)

    assert cards == []
    assert len(FakeBrowserSession.calls) == 1
    assert any(r.levelname == "ERROR" for r in caplog.records)


def test_collect_raw_cards_returns_empty_list_when_genuinely_no_results(monkeypatch, caplog):
    FakeBrowserSession.genuinely_empty = True
    monkeypatch.setattr(pagination_module, "BrowserSession", FakeBrowserSession)

    config = ScraperConfig(max_pages=1)
    with caplog.at_level("INFO", logger="g1_lgpd_scraper.pagination"):
        cards = pagination_module.collect_raw_cards(config)

    assert cards == []
    assert len(FakeBrowserSession.calls) == 1
    assert not any(r.levelname == "ERROR" for r in caplog.records)
    assert any("nao retornou nenhum resultado" in r.message for r in caplog.records)
