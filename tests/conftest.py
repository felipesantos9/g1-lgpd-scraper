from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "html"


@pytest.fixture
def rendered_10_html() -> str:
    return (FIXTURES_DIR / "rendered_10_items.html").read_text(encoding="utf-8")


@pytest.fixture
def rendered_20_html() -> str:
    return (FIXTURES_DIR / "rendered_20_items.html").read_text(encoding="utf-8")
