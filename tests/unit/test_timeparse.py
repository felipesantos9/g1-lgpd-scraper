from datetime import datetime, timedelta, timezone

from g1_lgpd_scraper.timeparse import parse_relative_pt

REFERENCE = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)


def test_parses_minutes():
    result = parse_relative_pt("há 45 minutos", REFERENCE)
    assert result == REFERENCE - timedelta(minutes=45)


def test_parses_hours():
    result = parse_relative_pt("há 7 horas", REFERENCE)
    assert result == REFERENCE - timedelta(hours=7)


def test_parses_days():
    result = parse_relative_pt("há 2 dias", REFERENCE)
    assert result == REFERENCE - timedelta(days=2)


def test_returns_none_for_unrecognized_text():
    assert parse_relative_pt("ontem", REFERENCE) is None


def test_returns_none_for_empty_text():
    assert parse_relative_pt(None, REFERENCE) is None
    assert parse_relative_pt("", REFERENCE) is None


def test_parses_absolute_date_used_for_older_results():
    result = parse_relative_pt("18/08/2026 13:23", REFERENCE)
    assert result == datetime(2026, 8, 18, 16, 23, tzinfo=timezone.utc)
