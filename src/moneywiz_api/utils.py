from datetime import datetime
from typing import Optional
from decimal import Decimal

_CUTOFF = datetime(2001, 1, 1, 0, 0, 0).timestamp()


def get_datetime(date: float) -> datetime:
    return datetime.fromtimestamp(date + _CUTOFF)


def get_date_iso(date: float) -> str:
    return get_datetime(date).date().isoformat()


def get_date(dt: datetime) -> float:
    return dt.timestamp() - _CUTOFF
