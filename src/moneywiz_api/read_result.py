"""Structured results for bounded MoneyWiz reads."""

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from moneywiz_api.types import ID


class LoadErrorKind(str, Enum):
    """Bounded classifications for records omitted from a read."""

    MISSING_FIELD = "missing_field"
    INVALID_VALUE = "invalid_value"
    VALIDATION = "validation"
    DUPLICATE_ID = "duplicate_id"
    DUPLICATE_GID = "duplicate_gid"


class RelationshipStorage(str, Enum):
    """Whether relationship storage is available and understood."""

    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SkippedRecord:
    """Identity-only diagnostic for one source row that was not parsed."""

    record_id: ID | str | None
    entity: str | None
    error: LoadErrorKind
    exception_type: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "entity": self.entity,
            "error": self.error.value,
            "exception_type": self.exception_type,
        }


@dataclass(frozen=True)
class RelationshipLoadReport:
    """Completeness evidence for one relationship storage layout."""

    storage: RelationshipStorage
    storage_name: str | None = None
    source_count: int = 0
    skipped: tuple[SkippedRecord, ...] = ()

    @property
    def parsed_count(self) -> int:
        return self.source_count - len(self.skipped)

    @property
    def complete(self) -> bool:
        return self.storage != RelationshipStorage.UNKNOWN and not self.skipped

    @property
    def status(self) -> str:
        if self.storage == RelationshipStorage.ABSENT:
            return "absent"
        if self.complete:
            return "complete"
        if self.parsed_count:
            return "partial"
        return "error"

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "complete": self.complete,
            "storage": self.storage.value,
            "storage_name": self.storage_name,
            "source_count": self.source_count,
            "parsed_count": self.parsed_count,
            "skipped": [item.as_dict() for item in self.skipped],
        }


@dataclass(frozen=True)
class ManagerLoadReport:
    """Completeness evidence for one manager load."""

    source_ids: tuple[ID | None, ...] = ()
    parsed_ids: tuple[ID, ...] = ()
    skipped: tuple[SkippedRecord, ...] = ()
    relationships: Mapping[str, RelationshipLoadReport] = field(default_factory=dict)
    observed: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "relationships", MappingProxyType(dict(self.relationships))
        )

    @classmethod
    def unloaded(cls) -> "ManagerLoadReport":
        """Return evidence that no complete manager observation was published."""
        return cls(observed=False)

    @property
    def source_count(self) -> int:
        return len(self.source_ids)

    @property
    def parsed_count(self) -> int:
        return len(self.parsed_ids)

    @property
    def complete(self) -> bool:
        return (
            self.observed
            and self.source_count == self.parsed_count
            and not self.skipped
            and all(report.complete for report in self.relationships.values())
        )

    @property
    def status(self) -> str:
        if not self.observed:
            return "unloaded"
        if self.complete:
            return "complete"
        if self.parsed_count or any(
            report.parsed_count for report in self.relationships.values()
        ):
            return "partial"
        return "error"

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "complete": self.complete,
            "source_count": self.source_count,
            "parsed_count": self.parsed_count,
            "source_ids": list(self.source_ids),
            "parsed_ids": list(self.parsed_ids),
            "skipped": [item.as_dict() for item in self.skipped],
            "relationships": {
                name: report.as_dict() for name, report in self.relationships.items()
            },
        }


@dataclass(frozen=True)
class ApiCompleteness:
    """Aggregate completeness for the managers included in a read."""

    managers: Mapping[str, ManagerLoadReport]

    def __post_init__(self) -> None:
        object.__setattr__(self, "managers", MappingProxyType(dict(self.managers)))

    @property
    def complete(self) -> bool:
        return bool(self.managers) and all(
            report.complete for report in self.managers.values()
        )

    @property
    def status(self) -> str:
        if self.complete:
            return "complete"
        if self.managers and all(
            report.status == "error" for report in self.managers.values()
        ):
            return "error"
        return "partial"

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "complete": self.complete,
            "managers": {
                name: report.as_dict() for name, report in self.managers.items()
            },
        }
