from g1_lgpd_scraper.models import SearchResult


def test_to_dict_contains_all_schema_fields():
    result = SearchResult(
        title="t",
        url="https://g1.globo.com/x.ghtml",
        summary="s",
        published_at_raw="há 1 dia",
        published_at_iso="2026-08-24T12:00:00+00:00",
        page_number=1,
        collected_at="2026-08-25T12:00:00+00:00",
        run_id="run-1",
        dedup_key="abc",
    )
    data = result.to_dict()
    expected_keys = {
        "title",
        "url",
        "summary",
        "published_at_raw",
        "published_at_iso",
        "page_number",
        "collected_at",
        "run_id",
        "dedup_key",
        "is_duplicate_of_previous_run",
    }
    assert set(data.keys()) == expected_keys
    assert data["is_duplicate_of_previous_run"] is False
