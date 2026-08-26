import csv
import json

from g1_lgpd_scraper.models import SearchResult
from g1_lgpd_scraper.storage.csv_writer import write_csv
from g1_lgpd_scraper.storage.json_writer import write_json


def make_result(url="https://g1.globo.com/x.ghtml"):
    return SearchResult(
        title="Título com acentuação",
        url=url,
        summary="Resumo",
        published_at_raw="há 1 dia",
        published_at_iso="2026-08-24T12:00:00+00:00",
        page_number=1,
        collected_at="2026-08-25T12:00:00+00:00",
        run_id="run-1",
        dedup_key="abc",
    )


def test_write_csv_roundtrip(tmp_path):
    path = tmp_path / "out.csv"
    write_csv([make_result()], path)
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["title"] == "Título com acentuação"
    assert rows[0]["url"] == "https://g1.globo.com/x.ghtml"


def test_write_csv_has_no_blank_lines_between_rows(tmp_path):
    path = tmp_path / "out.csv"
    write_csv([make_result("https://g1.globo.com/a.ghtml"), make_result("https://g1.globo.com/b.ghtml")], path)
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    non_empty = [line for line in lines if line.strip()]
    assert len(lines) == len(non_empty) == 3  # header + 2 rows, sem linhas em branco


def test_write_json_roundtrip(tmp_path):
    path = tmp_path / "out.json"
    write_json([make_result()], path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["title"] == "Título com acentuação"
