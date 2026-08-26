from g1_lgpd_scraper.parse.result_parser import parse_search_results


def test_parse_extracts_expected_field_count(rendered_10_html):
    cards = parse_search_results(rendered_10_html)
    assert len(cards) == 10


def test_parse_extracts_canonical_url_not_tracking_link(rendered_10_html):
    cards = parse_search_results(rendered_10_html)
    first = cards[0]
    assert first.url.startswith("https://g1.globo.com/")
    assert "measures.globo.com" not in first.url


def test_parse_extracts_title_and_summary(rendered_10_html):
    cards = parse_search_results(rendered_10_html)
    first = cards[0]
    assert first.title
    assert first.summary


def test_parse_extracts_relative_published_at(rendered_10_html):
    cards = parse_search_results(rendered_10_html)
    assert any(card.published_at_raw for card in cards)


def test_parse_assigns_page_number_by_batch(rendered_20_html):
    cards = parse_search_results(rendered_20_html, page_size=10)
    assert len(cards) == 20
    assert all(card.page_number == 1 for card in cards[:10])
    assert all(card.page_number == 2 for card in cards[10:])


def test_parse_skips_malformed_card_without_raising():
    html = """
    <div class="results__content all-search-results">
      <ul class="results__list">
        <li class="widget widget--info">
          <div class="widget--info__text-container">
            <div class="widget--info__title">Sem link, deve ser pulado</div>
          </div>
        </li>
        <li class="widget widget--info">
          <div class="widget--info__text-container">
            <a href="https://measures.globo.com/v1/click?u=https%3A%2F%2Fg1.globo.com%2Fok.ghtml">
              <div class="widget--info__title">Card valido</div>
            </a>
          </div>
        </li>
      </ul>
    </div>
    """
    cards = parse_search_results(html)
    assert len(cards) == 1
    assert cards[0].title == "Card valido"
    assert cards[0].url == "https://g1.globo.com/ok.ghtml"
