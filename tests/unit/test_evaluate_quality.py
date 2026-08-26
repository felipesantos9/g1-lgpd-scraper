"""Testa o script de avaliacao de qualidade (evaluation/evaluate_quality.py).

Carregado por caminho de arquivo (nao e um pacote instalavel) -- ver
specs/0002-data-quality-spec.md secao 4.
"""

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).parents[2] / "evaluation" / "evaluate_quality.py"
spec = importlib.util.spec_from_file_location("evaluate_quality", MODULE_PATH)
evaluate_quality = importlib.util.module_from_spec(spec)
sys.modules["evaluate_quality"] = evaluate_quality
spec.loader.exec_module(evaluate_quality)


REFERENCE = [
    {"title": "Titulo A", "url": "https://g1.globo.com/a.ghtml", "summary": "Resumo A completo", "published_at_raw": "há 1 dia"},
    {"title": "Titulo B", "url": "https://g1.globo.com/b.ghtml", "summary": "Resumo B completo", "published_at_raw": "há 2 dias"},
    {"title": "Titulo C (so na referencia)", "url": "https://g1.globo.com/c.ghtml", "summary": "Resumo C", "published_at_raw": "há 3 dias"},
]

SCRAPED = [
    {
        "title": "Titulo A", "url": "https://g1.globo.com/a.ghtml?utm=x", "summary": "Resumo A completo",
        "published_at_raw": "há 1 dia", "published_at_iso": "2026-08-24T12:00:00+00:00",
        "page_number": "1", "run_id": "r1", "collected_at": "2026-08-25T12:00:00+00:00", "dedup_key": "k1",
    },
    {
        "title": "Titulo B diferente", "url": "https://g1.globo.com/b.ghtml", "summary": "Resumo B totalmente distinto e sem nada em comum",
        "published_at_raw": "há 2 dias", "published_at_iso": "2026-08-23T12:00:00+00:00",
        "page_number": "1", "run_id": "r1", "collected_at": "2026-08-25T12:00:00+00:00", "dedup_key": "k2",
    },
    {
        "title": "Titulo D (so no scraper)", "url": "https://g1.globo.com/d.ghtml", "summary": "Resumo D",
        "published_at_raw": "há 4 dias", "published_at_iso": "2026-08-21T12:00:00+00:00",
        "page_number": "1", "run_id": "r1", "collected_at": "2026-08-25T12:00:00+00:00", "dedup_key": "k3",
    },
]


def test_match_records_splits_correctly():
    matched, only_ref, only_scr = evaluate_quality.match_records(REFERENCE, SCRAPED)
    assert len(matched) == 2
    assert len(only_ref) == 1
    assert only_ref[0]["title"] == "Titulo C (so na referencia)"
    assert len(only_scr) == 1
    assert only_scr[0]["title"] == "Titulo D (so no scraper)"


def test_canonical_url_ignores_query_string():
    assert evaluate_quality.canonical_url("https://g1.globo.com/a.ghtml?utm=x") == "https://g1.globo.com/a.ghtml"


def test_completeness_all_required_fields_present():
    result = evaluate_quality.evaluate_completeness(SCRAPED)
    assert result["required_fields_filled_pct"] == 100.0


def test_precision_detects_title_mismatch():
    matched, _, _ = evaluate_quality.match_records(REFERENCE, SCRAPED)
    result = evaluate_quality.evaluate_precision(matched)
    # item A: titulo igual; item B: titulo diferente -> 50%
    assert result["title_exact_match_pct"] == 50.0
    assert result["url_exact_match_pct"] == 100.0  # canonical_url ignora querystring


def test_accuracy_detects_dissimilar_summary():
    matched, _, _ = evaluate_quality.match_records(REFERENCE, SCRAPED)
    result = evaluate_quality.evaluate_accuracy(matched)
    # item A: resumo identico (similar); item B: resumo totalmente diferente (nao similar) -> 50%
    assert result["summary_similarity_pct"] == 50.0


def test_uniqueness_no_duplicates():
    result = evaluate_quality.evaluate_uniqueness(SCRAPED)
    assert result["duplicate_rate_pct"] == 0.0


def test_uniqueness_detects_duplicates():
    duplicated = SCRAPED + [SCRAPED[0]]
    result = evaluate_quality.evaluate_uniqueness(duplicated)
    assert result["duplicate_rate_pct"] > 0.0


def test_consistency_valid_iso_dates():
    result = evaluate_quality.evaluate_consistency(SCRAPED)
    assert result["valid_iso_date_pct"] == 100.0
    assert result["valid_page_number_pct"] == 100.0


def test_traceability_all_fields_present():
    result = evaluate_quality.evaluate_traceability(SCRAPED)
    assert result["fully_traceable_pct"] == 100.0


def test_build_report_has_all_sections():
    report = evaluate_quality.build_report(REFERENCE, SCRAPED)
    assert set(report.keys()) == {
        "counts", "completeness", "precision", "accuracy",
        "uniqueness", "timeliness", "consistency", "traceability",
    }
