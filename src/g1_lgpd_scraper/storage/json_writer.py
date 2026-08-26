"""Escrita de JSON. Ver docs/adr/0003-storage-format.md."""

import json
from pathlib import Path


def write_json(items: list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([item.to_dict() for item in items], f, ensure_ascii=False, indent=2)
