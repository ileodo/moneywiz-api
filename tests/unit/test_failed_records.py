from types import SimpleNamespace
from typing import Any, cast

import pytest

from moneywiz_api.managers.failed_record import FailedRecord
from moneywiz_api.managers.payee_manager import PayeeManager
from moneywiz_api.moneywiz_api import MoneywizApi


def test_manager_collects_failed_rows_and_keeps_valid_records():
    rows = [
        {"Z_ENT": 1, "Z_PK": 1},
        {"Z_ENT": 1, "Z_PK": 2},
        {"Z_ENT": 1, "Z_PK": 3},
    ]
    valid = SimpleNamespace(id=3, gid="valid", validate=lambda: None)
    invalid = SimpleNamespace(id=2, gid="invalid", validate=lambda: None)

    def validate_invalid():
        raise AssertionError("bad payee")

    invalid.validate = validate_invalid

    def create_record(row, _model_cls):
        if row["Z_PK"] == 1:
            raise RuntimeError("bad field")
        return invalid if row["Z_PK"] == 2 else valid

    accessor = SimpleNamespace(
        query_objects=lambda _types: rows,
        typename_for=lambda _ent: "Payee",
        schema_profile=SimpleNamespace(create_record=create_record),
    )
    manager = PayeeManager()
    manager.load(cast(Any, accessor))

    assert manager.get(3) is valid
    assert manager.get(2) is None
    assert [failure.raw for failure in manager.failed_records] == rows[:2]
    assert [failure.model_type for failure in manager.failed_records] == ["Payee"] * 2
    assert str(manager.failed_records[0].error) == "bad field"
    assert manager.failed_records[0].record is None
    assert manager.failed_records[1].record is invalid

    accessor.query_objects = lambda _types: rows[2:]
    manager.load(cast(Any, accessor))
    assert manager.failed_records == []


def test_api_exposes_manager_failures():
    api = MoneywizApi.__new__(MoneywizApi)
    manager = PayeeManager()
    failure = FailedRecord("Payee", {"Z_PK": 1}, ValueError("invalid"))
    manager.failed_records.append(failure)
    api.account_manager = cast(Any, PayeeManager())
    api.payee_manager = manager
    api.category_manager = cast(Any, PayeeManager())
    api.transaction_manager = cast(Any, PayeeManager())
    api.investment_holding_manager = cast(Any, PayeeManager())
    api.tag_manager = cast(Any, PayeeManager())
    assert api.failed_records == [failure]


@pytest.mark.parametrize("failure_stage", ["conversion", "validation"])
def test_strict_load_raises_first_record_error(failure_stage):
    row = {"Z_ENT": 1, "Z_PK": 1}

    def validate():
        raise AssertionError("bad payee")

    def create_record(_row, _model_cls):
        if failure_stage == "conversion":
            raise ValueError("bad field")
        return SimpleNamespace(validate=validate)

    accessor = SimpleNamespace(
        query_objects=lambda _types: [row],
        typename_for=lambda _ent: "Payee",
        schema_profile=SimpleNamespace(create_record=create_record),
    )
    manager = PayeeManager()

    with pytest.raises((ValueError, AssertionError)):
        manager.load(cast(Any, accessor), strict=True)

    assert manager.failed_records == []


def test_api_passes_strict_mode_to_managers():
    api = MoneywizApi.__new__(MoneywizApi)
    api.strict = True
    api.accessor = cast(Any, object())
    calls = []
    manager = SimpleNamespace(
        load=lambda accessor, strict: calls.append((accessor, strict))
    )
    api.account_manager = cast(Any, manager)
    api.payee_manager = cast(Any, manager)
    api.category_manager = cast(Any, manager)
    api.transaction_manager = cast(Any, manager)
    api.investment_holding_manager = cast(Any, manager)
    api.tag_manager = cast(Any, manager)

    api.load()

    assert calls == [(api.accessor, True)] * 6
