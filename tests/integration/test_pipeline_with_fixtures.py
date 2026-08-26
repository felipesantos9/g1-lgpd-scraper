"""Integracao parse -> dedup -> store, usando fixtures de HTML real. Sem rede/browser."""

from datetime import datetime, timezone

from g1_lgpd_scraper.dedup import dedup_within_run, make_dedup_key
from g1_lgpd_scraper.models import SearchResult
from g1_lgpd_scraper.parse.result_parser import parse_search_results
from g1_lgpd_scraper.storage.csv_writer import write_csv
from g1_lgpd_scraper.storage.json_writer import write_json
from g1_lgpd_scraper.timeparse import parse_relative_pt


def test_full_pipeline_produces_valid_csv_and_json(rendered_20_html, tmp_path):
    reference = datetime.now(timezone.utc)

    cards = parse_search_results(rendered_20_html)
    assert len(cards) == 20

    results = []
    for card in cards:
        published_at = parse_relative_pt(card.published_at_raw, reference)
        results.append(
            SearchResult(
                title=card.title,
                url=card.url,
                summary=card.summary,
                published_at_raw=card.published_at_raw,
                published_at_iso=published_at.isoformat() if published_at else None,
                page_number=card.page_number,
                collected_at=reference.isoformat(),
                run_id="test-run",
                dedup_key=make_dedup_key(card.url),
            )
        )

    results = dedup_within_run(results)
    assert all(r.title and r.url for r in results)

    csv_path = tmp_path / "out.csv"
    json_path = tmp_path / "out.json"
    write_csv(results, csv_path)
    write_json(results, json_path)

    assert csv_path.exists()
    assert json_path.exists()
    assert csv_path.read_text(encoding="utf-8").count("\n") >= len(results)
