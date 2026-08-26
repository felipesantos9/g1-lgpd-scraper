"""Schema do registro coletado."""

from dataclasses import dataclass, field, asdict


@dataclass
class RawCard:
    """Dados extraidos diretamente de um card de resultado."""

    title: str | None
    url: str | None
    summary: str | None
    published_at_raw: str | None
    page_number: int


@dataclass
class SearchResult:
    """Registro final, pronto para armazenamento."""

    title: str | None
    url: str | None
    summary: str | None
    published_at_raw: str | None
    published_at_iso: str | None
    page_number: int
    collected_at: str
    run_id: str
    dedup_key: str
    is_duplicate_of_previous_run: bool = field(default=False)

    def to_dict(self) -> dict:
        return asdict(self)
