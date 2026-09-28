import json
from typing import cast
from moneywiz_api.database_accessor import DatabaseAccessor
from contextlib import contextmanager

import pytest

from moneywiz_api.managers.record_manager import RecordManager
from moneywiz_api.model.record import Record
from moneywiz_api.read_result import (
    ApiCompleteness,
    LoadErrorKind,
    ManagerLoadReport,
    RelationshipLoadReport,
    RelationshipStorage,
)


class ExampleRecord(Record):
    pass


class ExampleManager(RecordManager):
    @property
    def ents(self):
        return {"ExampleRecord": ExampleRecord}


def record_row(record_id=1, gid="record-1", ent=1):
    return {
        "Z_ENT": ent,
        "ZOBJECTCREATIONDATE": 0.0,
        "ZGID": gid,
        "Z_PK": record_id,
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("ZGID", b"binary-id"),
        ("Z_PK", "1"),
        ("Z_ENT", True),
    ],
)
def test_record_validation_rejects_coerced_identity(field, value) -> None:
    row = record_row()
    row[field] = value
    with pytest.raises(AssertionError):
        ExampleRecord(row).validate()


class RecordAccessor:
    def __init__(self, rows, typenames=None):
        self.rows = rows
        self.typenames = typenames or {1: "ExampleRecord"}

    @contextmanager
    def read_transaction(self):
        yield

    def query_objects(self, typenames):
        return [
            row
            for row in self.rows
            if "Z_ENT" not in row or self.typenames.get(row["Z_ENT"]) in typenames
        ]

    def typename_for(self, ent_id):
        return self.typenames.get(ent_id)


def test_report_counts_duplicate_rows_without_partial_mutation() -> None:
    manager = ExampleManager()
    rows = [
        record_row(),
        record_row(gid="duplicate-id"),
        record_row(record_id=2),
        record_row(record_id=3, gid="record-3", ent=2),
    ]

    report = manager.load(
        cast(
            DatabaseAccessor,
            RecordAccessor(rows, {1: "ExampleRecord", 2: "FutureRecord"}),
        )
    )

    assert report.source_ids == (1, 1, 2)
    assert report.parsed_ids == (1,)
    assert [item.error for item in report.skipped] == [
        LoadErrorKind.DUPLICATE_ID,
        LoadErrorKind.DUPLICATE_GID,
    ]
    assert report.observed
    assert report.status == "partial"
    assert list(manager.records()) == [1]


@pytest.mark.parametrize("exception_type", [ValueError, RuntimeError])
def test_construction_error_is_bounded_without_raw_value(
    caplog, exception_type
) -> None:
    class BrokenRecord(Record):
        def __init__(self, _row):
            raise exception_type("PRIVATE_PAYLOAD")

    class BrokenManager(RecordManager):
        @property
        def ents(self):
            return {"ExampleRecord": BrokenRecord}

    caplog.set_level("DEBUG")
    report = BrokenManager().load(
        cast(DatabaseAccessor, RecordAccessor([record_row()]))
    )

    assert report.skipped[0].error == LoadErrorKind.INVALID_VALUE
    assert report.skipped[0].exception_type == exception_type.__name__
    assert "PRIVATE_PAYLOAD" not in json.dumps(report.as_dict())
    assert "PRIVATE_PAYLOAD" not in caplog.text


def test_report_mappings_cannot_change_completeness_after_publication() -> None:
    relationships = {
        "transaction_tags": RelationshipLoadReport(RelationshipStorage.UNKNOWN)
    }
    report = ManagerLoadReport(relationships=relationships)
    managers = {"transactions": report}
    completeness = ApiCompleteness(managers)

    relationships.clear()
    managers.clear()
    assert not report.complete
    assert not completeness.complete
    mutable_relationships = cast(
        dict[str, RelationshipLoadReport], report.relationships
    )
    mutable_managers = cast(dict[str, ManagerLoadReport], completeness.managers)
    with pytest.raises(TypeError):
        mutable_relationships["transaction_tags"] = RelationshipLoadReport(
            RelationshipStorage.ABSENT
        )
    with pytest.raises(TypeError):
        mutable_managers["transactions"] = ManagerLoadReport()


def test_missing_field_is_reported() -> None:
    row = record_row()
    del row["Z_ENT"]

    report = ExampleManager().load(cast(DatabaseAccessor, RecordAccessor([row])))

    assert report.skipped[0].error == LoadErrorKind.MISSING_FIELD
    assert report.status == "error"
    assert not report.complete


def test_each_load_resets_records_and_diagnostics() -> None:
    manager = ExampleManager()
    manager.load(
        cast(
            DatabaseAccessor,
            RecordAccessor([record_row(), record_row(gid="duplicate-id")]),
        )
    )

    report = manager.load(
        cast(
            DatabaseAccessor, RecordAccessor([record_row(record_id=4, gid="record-4")])
        )
    )

    assert report.complete
    assert report.source_ids == (4,)
    assert report.parsed_ids == (4,)
    assert list(manager.records()) == [4]
    assert manager.load_errors == []


def test_failed_direct_reload_discards_state_and_can_retry() -> None:
    manager = ExampleManager()
    assert manager.load_report.as_dict()["status"] == "unloaded"
    manager.load(cast(DatabaseAccessor, RecordAccessor([record_row()])))

    class FailingAccessor(RecordAccessor):
        def query_objects(self, _typenames):
            raise RuntimeError("synthetic reload failure")

    with pytest.raises(RuntimeError, match="synthetic reload failure"):
        manager.load(cast(DatabaseAccessor, FailingAccessor([])))

    assert manager.load_report.status == "unloaded"
    assert not manager.load_report.complete
    assert manager.records() == {}

    report = manager.load(cast(DatabaseAccessor, RecordAccessor([])))
    assert report.complete


@pytest.mark.parametrize("interruption_type", [KeyboardInterrupt, SystemExit])
def test_interrupted_reload_discards_partial_state_and_reraises(
    interruption_type,
) -> None:
    manager = ExampleManager()
    manager.load(
        cast(
            DatabaseAccessor, RecordAccessor([record_row(record_id=9, gid="record-9")])
        )
    )
    interruption = interruption_type("synthetic interruption")

    class InterruptingAccessor(RecordAccessor):
        def __init__(self):
            super().__init__([record_row(), record_row(record_id=2, gid="record-2")])
            self.lookups = 0

        def typename_for(self, ent_id):
            self.lookups += 1
            if self.lookups == 2:
                raise interruption
            return super().typename_for(ent_id)

    with pytest.raises(interruption_type) as error:
        manager.load(cast(DatabaseAccessor, InterruptingAccessor()))

    assert error.value is interruption
    assert manager.records() == {}
    assert manager._gid_to_id == {}
    assert manager.load_report.status == "unloaded"

    report = manager.load(
        cast(
            DatabaseAccessor, RecordAccessor([record_row(record_id=3, gid="record-3")])
        )
    )

    assert report.complete
    assert list(manager.records()) == [3]
