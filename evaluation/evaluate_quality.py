"""Avalia a qualidade dos dados coletados contra uma amostra de referencia manual.

Contrato completo em specs/0002-data-quality-spec.md. Uso:
    python evaluation/evaluate_quality.py --reference evaluation/reference_sample.csv \
        --scraped data/processed/latest.csv
"""

import argparse
import csv
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

SIMILARITY_THRESHOLD = 0.8


def canonical_url(url: str) -> str:
    if not url:
        return ""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def match_records(reference: list[dict], scraped: list[dict]):
    ref_by_url = {canonical_url(r["url"]): r for r in reference if r.get("url")}
    scr_by_url = {canonical_url(r["url"]): r for r in scraped if r.get("url")}

    matched = [(ref_by_url[u], scr_by_url[u]) for u in ref_by_url.keys() & scr_by_url.keys()]
    only_reference = [ref_by_url[u] for u in ref_by_url.keys() - scr_by_url.keys()]
    only_scraped = [scr_by_url[u] for u in scr_by_url.keys() - ref_by_url.keys()]
    return matched, only_reference, only_scraped


def is_valid_iso8601(value: str) -> bool:
    if not value:
        return False
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


def evaluate_completeness(scraped: list[dict]) -> dict:
    total = len(scraped)
    if total == 0:
        return {"required_fields_filled_pct": 0.0, "optional_fields_filled_pct": 0.0}
    required_ok = sum(1 for r in scraped if r.get("title") and r.get("url"))
    optional_ok = sum(1 for r in scraped if r.get("summary") and r.get("published_at_raw"))
    return {
        "required_fields_filled_pct": round(100 * required_ok / total, 1),
        "optional_fields_filled_pct": round(100 * optional_ok / total, 1),
    }


def evaluate_precision(matched: list[tuple]) -> dict:
    if not matched:
        return {"title_exact_match_pct": None, "url_exact_match_pct": None}
    title_matches = sum(1 for ref, scr in matched if ref["title"].strip() == scr["title"].strip())
    url_matches = sum(1 for ref, scr in matched if canonical_url(ref["url"]) == canonical_url(scr["url"]))
    return {
        "title_exact_match_pct": round(100 * title_matches / len(matched), 1),
        "url_exact_match_pct": round(100 * url_matches / len(matched), 1),
    }


def evaluate_accuracy(matched: list[tuple]) -> dict:
    if not matched:
        return {"summary_similarity_pct": None}
    similar = 0
    for ref, scr in matched:
        ratio = SequenceMatcher(None, ref.get("summary", ""), scr.get("summary", "")).ratio()
        if ratio >= SIMILARITY_THRESHOLD:
            similar += 1
    return {"summary_similarity_pct": round(100 * similar / len(matched), 1)}


def evaluate_uniqueness(scraped: list[dict]) -> dict:
    total = len(scraped)
    if total == 0:
        return {"duplicate_rate_pct": 0.0}
    unique_keys = {r.get("dedup_key") for r in scraped}
    return {"duplicate_rate_pct": round(100 * (1 - len(unique_keys) / total), 1)}


def evaluate_timeliness(matched: list[tuple], reference: list[dict], scraped: list[dict]) -> dict:
    coverage = None
    if reference:
        ref_urls = {canonical_url(r["url"]) for r in reference}
        scr_urls = {canonical_url(r["url"]) for r in scraped}
        coverage = round(100 * len(ref_urls & scr_urls) / len(ref_urls), 1)
    return {"reference_coverage_pct": coverage}


def evaluate_consistency(scraped: list[dict]) -> dict:
    total = len(scraped)
    if total == 0:
        return {"valid_iso_date_pct": None, "valid_page_number_pct": 0.0}
    with_raw_date = [r for r in scraped if r.get("published_at_raw")]
    valid_iso = sum(1 for r in with_raw_date if is_valid_iso8601(r.get("published_at_iso", "")))
    valid_page = sum(1 for r in scraped if str(r.get("page_number", "")).isdigit() and int(r["page_number"]) >= 1)
    return {
        "valid_iso_date_pct": round(100 * valid_iso / len(with_raw_date), 1) if with_raw_date else None,
        "valid_page_number_pct": round(100 * valid_page / total, 1),
    }


def evaluate_traceability(scraped: list[dict]) -> dict:
    total = len(scraped)
    if total == 0:
        return {"fully_traceable_pct": 0.0}
    traceable = sum(1 for r in scraped if r.get("run_id") and r.get("collected_at") and r.get("page_number"))
    return {"fully_traceable_pct": round(100 * traceable / total, 1)}


def build_report(reference: list[dict], scraped: list[dict]) -> dict:
    matched, only_reference, only_scraped = match_records(reference, scraped)
    return {
        "counts": {
            "reference_total": len(reference),
            "scraped_total": len(scraped),
            "matched": len(matched),
            "only_in_reference": len(only_reference),
            "only_in_scraped": len(only_scraped),
        },
        "completeness": evaluate_completeness(scraped),
        "precision": evaluate_precision(matched),
        "accuracy": evaluate_accuracy(matched),
        "uniqueness": evaluate_uniqueness(scraped),
        "timeliness": evaluate_timeliness(matched, reference, scraped),
        "consistency": evaluate_consistency(scraped),
        "traceability": evaluate_traceability(scraped),
    }


def format_report_markdown(report: dict) -> str:
    lines = ["# Relatório de qualidade de dados", ""]
    for section, values in report.items():
        lines.append(f"## {section}")
        for key, value in values.items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--scraped", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None, help="Se informado, grava o relatorio em markdown neste caminho")
    args = parser.parse_args()

    reference = read_csv(args.reference)
    scraped = read_csv(args.scraped)
    report = build_report(reference, scraped)

    markdown = format_report_markdown(report)
    print(markdown)
    if args.output:
        args.output.write_text(markdown, encoding="utf-8")


if __name__ == "__main__":
    main()
