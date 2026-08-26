"""Orquestracao fetch -> parse -> dedup -> store."""

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from g1_lgpd_scraper.config import ScraperConfig
from g1_lgpd_scraper.dedup import (
    dedup_within_run,
    load_previous_keys,
    make_dedup_key,
    mark_duplicates_across_runs,
)
from g1_lgpd_scraper.logging_config import configure_logging
from g1_lgpd_scraper.models import SearchResult
from g1_lgpd_scraper.pagination import collect_raw_cards
from g1_lgpd_scraper.storage.csv_writer import write_csv
from g1_lgpd_scraper.storage.json_writer import write_json
from g1_lgpd_scraper.timeparse import parse_relative_pt


def _slugify(value: str) -> str:
    return re.sub(r"[^\w\-]+", "_", value).strip("_") or "query"


@dataclass
class RunSummary:
    run_id: str
    total_collected: int
    total_after_dedup: int
    total_duplicate_of_previous_run: int
    csv_path: Path
    json_path: Path


def run(config: ScraperConfig) -> RunSummary:
    run_id = uuid.uuid4().hex[:12]
    logger = configure_logging(run_id=run_id)
    logger.info("iniciando execucao query=%r max_pages=%d", config.query, config.max_pages)

    reference_time = datetime.now(timezone.utc)
    raw_cards = collect_raw_cards(config)
    logger.info("cards brutos coletados: %d", len(raw_cards))

    results: list[SearchResult] = []
    for card in raw_cards:
        published_at = parse_relative_pt(card.published_at_raw, reference_time)
        results.append(
            SearchResult(
                title=card.title,
                url=card.url,
                summary=card.summary,
                published_at_raw=card.published_at_raw,
                published_at_iso=published_at.isoformat() if published_at else None,
                page_number=card.page_number,
                collected_at=reference_time.isoformat(),
                run_id=run_id,
                dedup_key=make_dedup_key(card.url),
            )
        )

    results = dedup_within_run(results)

    latest_json_path = config.output_dir / "latest.json"
    previous_keys = load_previous_keys(latest_json_path)
    results = mark_duplicates_across_runs(results, previous_keys)
    duplicate_count = sum(1 for r in results if r.is_duplicate_of_previous_run)

    timestamp = reference_time.strftime("%Y%m%d_%H%M%S")
    query_slug = _slugify(config.query)
    csv_path = config.output_dir / f"g1_lgpd_{query_slug}_{timestamp}.csv"
    json_path = config.output_dir / f"g1_lgpd_{query_slug}_{timestamp}.json"

    write_csv(results, csv_path)
    write_json(results, json_path)
    write_csv(results, config.output_dir / "latest.csv")
    write_json(results, latest_json_path)

    logger.info(
        "execucao concluida: %d coletados, %d apos dedup interno, %d ja vistos em execucao anterior",
        len(raw_cards),
        len(results),
        duplicate_count,
    )

    return RunSummary(
        run_id=run_id,
        total_collected=len(raw_cards),
        total_after_dedup=len(results),
        total_duplicate_of_previous_run=duplicate_count,
        csv_path=csv_path,
        json_path=json_path,
    )
