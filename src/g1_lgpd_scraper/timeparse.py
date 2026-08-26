"""Interpretacao da data de publicacao exibida na busca do G1.

A pagina de busca mostra dois formatos, confirmados na coleta real:
resultados recentes usam tempo relativo em portugues ("ha 45 minutos", "ha 2 dias");
resultados mais antigos trocam para uma data absoluta no formato "dd/mm/aaaa HH:MM".
"""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")

_UNIT_TO_KWARG = {
    "segundo": "seconds",
    "minuto": "minutes",
    "hora": "hours",
    "dia": "days",
    "semana": "weeks",
    "mes": "days",  # aproximacao: 1 mes = 30 dias
    "ano": "days",  # aproximacao: 1 ano = 365 dias
}
_UNIT_MULTIPLIER = {"mes": 30, "ano": 365}

_RELATIVE_RE = re.compile(
    r"h[áa]\s+(\d+)\s+(segundo|minuto|hora|dia|semana|m[êe]s|ano)s?", re.IGNORECASE
)
_ABSOLUTE_RE = re.compile(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})")


def _parse_relative(text: str, reference: datetime) -> datetime | None:
    normalized = text.lower().replace("mês", "mes")
    match = _RELATIVE_RE.search(normalized)
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2).replace("ê", "e")
    kwarg = _UNIT_TO_KWARG.get(unit)
    if kwarg is None:
        return None

    multiplier = _UNIT_MULTIPLIER.get(unit, 1)
    delta = timedelta(**{kwarg: amount * multiplier})
    return reference - delta


def _parse_absolute(text: str, reference: datetime) -> datetime | None:
    match = _ABSOLUTE_RE.search(text)
    if not match:
        return None
    naive = datetime.strptime(f"{match.group(1)} {match.group(2)}", "%d/%m/%Y %H:%M")
    localized = naive.replace(tzinfo=_BRAZIL_TZ)
    return localized.astimezone(reference.tzinfo)


def parse_relative_pt(text: str | None, reference: datetime) -> datetime | None:
    """Converte o texto de data da busca (relativo ou absoluto) para datetime.

    Retorna None se o texto nao casar com nenhum dos dois formatos conhecidos.
    """
    if not text:
        return None
    return _parse_relative(text, reference) or _parse_absolute(text, reference)
