"""Escrita de CSV. Ver docs/adr/0003-storage-format.md."""

import csv
from pathlib import Path

FIELDNAMES = [
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
]


def write_csv(items: list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for item in items:
            writer.writerow(item.to_dict())
