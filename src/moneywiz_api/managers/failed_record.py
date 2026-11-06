from dataclasses import dataclass
from typing import Any, Dict

from moneywiz_api.model.record import Record


@dataclass(frozen=True)
class FailedRecord:
    """A row that could not be converted to, or validated as, a record."""

    model_type: str
    raw: Dict[str, Any]
    error: Exception
    record: Record | None = None
