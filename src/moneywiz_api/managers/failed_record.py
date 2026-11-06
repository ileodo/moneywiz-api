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


class RecordLoadError(Exception):
    """A record failed during a load configured to raise errors."""

    def __init__(self, failure: FailedRecord):
        self.failure = failure
        super().__init__(
            f"Failed to load {failure.model_type} row "
            f"{failure.raw.get('Z_PK')}: {failure.error}"
        )
