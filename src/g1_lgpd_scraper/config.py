"""Configuração da execução do scraper."""

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus


@dataclass(frozen=True)
class ScraperConfig:
    query: str = "lgpd"
    start_page: int = 1
    max_pages: int = 5
    output_dir: Path = Path("data/processed")
    request_delay_seconds: float = 1.0
    request_timeout_seconds: float = 30.0
    max_retries: int = 3
    base_url: str = "https://g1.globo.com/busca/"

    def search_url(self) -> str:
        return f"{self.base_url}?q={quote_plus(self.query)}"
