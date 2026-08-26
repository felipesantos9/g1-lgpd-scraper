import json
from datetime import datetime, timezone

from g1_lgpd_scraper.dedup import (
    canonical_url,
    dedup_within_run,
    load_previous_keys,
    make_dedup_key,
    mark_duplicates_across_runs,
)
from g1_lgpd_scraper.models import SearchResult


def make_result(url: str) -> SearchResult:
    now = datetime.now(timezone.utc).isoformat()
    return SearchResult(
        title="t",
        url=url,
        summary="s",
        published_at_raw=None,
        published_at_iso=None,
        page_number=1,
        collected_at=now,
        run_id="run-1",
        dedup_key=make_dedup_key(url),
    )


def test_canonical_url_strips_query_and_fragment():
    assert canonical_url("https://g1.globo.com/x.ghtml?utm=abc#frag") == "https://g1.globo.com/x.ghtml"


def test_make_dedup_key_is_stable_regardless_of_query_string():
    key_a = make_dedup_key("https://g1.globo.com/x.ghtml?utm=abc")
    key_b = make_dedup_key("https://g1.globo.com/x.ghtml?utm=xyz")
    assert key_a == key_b


def test_dedup_within_run_keeps_first_occurrence():
    items = [make_result("https://g1.globo.com/a.ghtml"), make_result("https://g1.globo.com/a.ghtml")]
    deduped = dedup_within_run(items)
    assert len(deduped) == 1


def test_load_previous_keys_missing_file_returns_empty_set(tmp_path):
    assert load_previous_keys(tmp_path / "does_not_exist.json") == set()


def test_load_previous_keys_reads_existing_dedup_keys(tmp_path):
    path = tmp_path / "latest.json"
    path.write_text(json.dumps([{"dedup_key": "abc123"}]), encoding="utf-8")
    assert load_previous_keys(path) == {"abc123"}


def test_mark_duplicates_across_runs_sets_flag():
    item = make_result("https://g1.globo.com/a.ghtml")
    marked = mark_duplicates_across_runs([item], {item.dedup_key})
    assert marked[0].is_duplicate_of_previous_run is True


def test_mark_duplicates_across_runs_leaves_new_items_unflagged():
    item = make_result("https://g1.globo.com/a.ghtml")
    marked = mark_duplicates_across_runs([item], {"outra-key"})
    assert marked[0].is_duplicate_of_previous_run is False
