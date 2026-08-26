import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from g1_lgpd_scraper.fetch.browser_client import (
    LOAD_MORE_SELECTOR,
    NOT_FOUND_SELECTOR,
    RESULTS_ITEM_SELECTOR,
    BrowserFetchError,
    BrowserSession,
)


class FlakyPage:
    """Simula page.goto falhando N vezes antes de suceder."""

    def __init__(self, fail_times: int):
        self._fail_times = fail_times
        self.goto_calls = 0

    def goto(self, url, wait_until=None, timeout=None):
        self.goto_calls += 1
        if self.goto_calls <= self._fail_times:
            raise TimeoutError("timeout simulado")

    def wait_for_selector(self, selector, timeout=None):
        pass


def make_session(page, max_retries=3, delay_seconds=0):
    session = BrowserSession(timeout_ms=1000, max_retries=max_retries, delay_seconds=delay_seconds)
    session._page = page
    return session


def test_navigate_retries_on_transient_failure_and_succeeds():
    page = FlakyPage(fail_times=1)
    session = make_session(page, max_retries=3)

    session._navigate("https://example.com")

    assert page.goto_calls == 2


def test_navigate_raises_browser_fetch_error_after_exhausting_retries():
    page = FlakyPage(fail_times=5)
    session = make_session(page, max_retries=2)

    with pytest.raises(BrowserFetchError):
        session._navigate("https://example.com")

    assert page.goto_calls == 2


class FakeLocator:
    def __init__(self, count_value):
        self._count = count_value
        self.first = self

    def count(self):
        return self._count

    def click(self):
        pass


class ScriptedPage:
    """Fake page para testar load_up_to_page: contagem de cada seletor eh
    definida por chamada (lista) ou fixa (int)."""

    def __init__(self, locator_counts, content="<html>conteudo</html>", wait_for_function_raises=False):
        self._locator_counts = locator_counts
        self._content = content
        self._call_index: dict = {}
        self._wait_for_function_raises = wait_for_function_raises

    def goto(self, url, wait_until=None, timeout=None):
        pass

    def wait_for_selector(self, selector, timeout=None):
        pass

    def wait_for_function(self, expression, arg=None, timeout=None):
        if self._wait_for_function_raises:
            raise PlaywrightTimeoutError("timeout simulado")

    def locator(self, selector):
        counts = self._locator_counts.get(selector, 0)
        if isinstance(counts, list):
            idx = self._call_index.get(selector, 0)
            value = counts[min(idx, len(counts) - 1)]
            self._call_index[selector] = idx + 1
        else:
            value = counts
        return FakeLocator(value)

    def content(self):
        return self._content


def test_load_up_to_page_detects_genuinely_empty_search():
    page = ScriptedPage({NOT_FOUND_SELECTOR: 1})
    session = make_session(page)

    result = session.load_up_to_page("https://example.com", target_page=1)

    assert result.genuinely_empty is True
    assert result.html == "<html>conteudo</html>"


def test_load_up_to_page_not_empty_when_results_present():
    page = ScriptedPage({NOT_FOUND_SELECTOR: 0, LOAD_MORE_SELECTOR: 0})
    session = make_session(page)

    result = session.load_up_to_page("https://example.com", target_page=1)

    assert result.genuinely_empty is False


def test_load_up_to_page_clicks_load_more_when_not_genuinely_empty():
    page = ScriptedPage(
        {
            NOT_FOUND_SELECTOR: 0,
            LOAD_MORE_SELECTOR: 1,
            RESULTS_ITEM_SELECTOR: 10,
        }
    )
    session = make_session(page)

    result = session.load_up_to_page("https://example.com", target_page=2)

    assert result.genuinely_empty is False


def test_load_up_to_page_stops_when_click_brings_no_new_items():
    page = ScriptedPage(
        {
            NOT_FOUND_SELECTOR: 0,
            LOAD_MORE_SELECTOR: 1,
            RESULTS_ITEM_SELECTOR: 10,
        },
        wait_for_function_raises=True,
    )
    session = make_session(page)

    result = session.load_up_to_page("https://example.com", target_page=3)

    assert result.genuinely_empty is False
