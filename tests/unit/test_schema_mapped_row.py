from decimal import Decimal

import pytest

from moneywiz_api.model.record import Record
from moneywiz_api.model.schema_mapped_row import decimal_field, mapped_row
from moneywiz_api.model.tag import Tag


class ExampleRecord(Record):
    FIELDS = {
        "amount": decimal_field("ZAMOUNT"),
    }


def _record_columns():
    return {
        "Z_ENT": 1,
        "ZOBJECTCREATIONDATE": 0,
        "ZGID": "gid",
        "Z_PK": 1,
    }


def test_schema_mapped_row_merges_inherited_fields_and_converts_values():
    row = mapped_row({**_record_columns(), "ZAMOUNT": 12.34}, ExampleRecord)

    assert row.get("id") == 1
    assert row.get("amount") == Decimal("12.34")


def test_schema_mapped_row_reports_missing_columns():
    row = mapped_row(_record_columns(), ExampleRecord)

    with pytest.raises(KeyError, match="Could not resolve field amount"):
        row.get("amount")


def test_model_constructor_accepts_raw_row_with_schema_fields():
    tag = Tag({**_record_columns(), "ZNAME6": "tax", "ZUSER8": 2})

    assert tag.name == "tax"
    assert tag.user == 2
