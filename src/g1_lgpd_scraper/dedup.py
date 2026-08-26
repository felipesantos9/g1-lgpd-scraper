"""Deduplicacao."""

import hashlib
import json
import logging
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

logger = logging.getLogger("g1_lgpd_scraper.dedup")


def canonical_url(url: str) -> str:
    """Remove query string e fragmento, mantendo apenas scheme+host+path."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def make_dedup_key(url: str) -> str:
    return hashlib.sha256(canonical_url(url).encode("utf-8")).hexdigest()


def dedup_within_run(items: list) -> list:
    """Mantem apenas a primeira ocorrencia de cada dedup_key. Loga repetidas."""
    seen: set[str] = set()
    deduped = []
    duplicates = 0
    for item in items:
        if item.dedup_key in seen:
            duplicates += 1
            continue
        seen.add(item.dedup_key)
        deduped.append(item)
    if duplicates:
        logger.warning("%d registros duplicados dentro da mesma execucao foram descartados", duplicates)
    return deduped


def load_previous_keys(latest_json_path: Path) -> set[str]:
    """Carrega as dedup_key da execucao anterior, se o arquivo existir e for legivel."""
    if not latest_json_path.exists():
        return set()
    try:
        with open(latest_json_path, encoding="utf-8") as f:
            previous = json.load(f)
        return {record["dedup_key"] for record in previous if "dedup_key" in record}
    except (json.JSONDecodeError, OSError, KeyError, TypeError):
        logger.warning("nao foi possivel carregar dedup_key de %s; tratando como execucao inicial", latest_json_path)
        return set()


def mark_duplicates_across_runs(items: list, previous_keys: set[str]) -> list:
    for item in items:
        if item.dedup_key in previous_keys:
            item.is_duplicate_of_previous_run = True
    return items
