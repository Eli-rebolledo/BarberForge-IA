"""Hora local de la barbería. Las fechas y horas de las citas se guardan en hora local (sin zona)."""
from datetime import UTC, date, datetime, time
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.config import get_settings


@lru_cache
def zona() -> ZoneInfo:
    return ZoneInfo(get_settings().zona_horaria)


def ahora_local() -> datetime:
    """Fecha y hora actual en la zona de la barbería, sin tzinfo (igual que las citas)."""
    return datetime.now(zona()).replace(tzinfo=None)


def hoy() -> date:
    return ahora_local().date()


def ahora_utc() -> datetime:
    return datetime.now(UTC)


def hora12(t: time) -> str:
    """09:30 -> 9:30 a. m.; 14:00 -> 2:00 p. m."""
    h = t.hour % 12 or 12
    return f"{h}:{t.minute:02d} {'a. m.' if t.hour < 12 else 'p. m.'}"
