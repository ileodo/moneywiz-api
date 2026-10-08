from dataclasses import dataclass
from decimal import Decimal
from unittest.mock import Mock

import pytest

from moneywiz_api.model.record import Record
from moneywiz_api import DEFAULT_SCHEMA_PROFILE
from moneywiz_api.schema.schema_fields import decimal_field
from moneywiz_api.model.tag import Tag
from moneywiz_api.model.category import Category
from moneywiz_api.schema.schema_fields import schema_field
from moneywiz_api import SchemaProfile


@dataclass
class ExampleRecord(Record):
    amount: Decimal


EXAMPLE_PROFILE = SchemaProfile(
    {
        **DEFAULT_SCHEMA_PROFILE.column_map,
        ExampleRecord.__name__: {"amount": decimal_field("ZAMOUNT")},
    }
)


def _record_columns():
    return {
        "Z_ENT": 1,
        "ZOBJECTCREATIONDATE": 0,
        "ZGID": "gid",
        "Z_PK": 1,
    }


def test_schema_profile_resolves_inherited_fields_and_converts_values():
    row = {**_record_columns(), "ZAMOUNT": 12.34}

    record = EXAMPLE_PROFILE.create_record(row, ExampleRecord)
    assert record.id == 1
    assert record.amount == Decimal("12.34")


def test_schema_fields_reports_missing_columns():
    with pytest.raises(RuntimeError, match="amount: Could not resolve field amount"):
        EXAMPLE_PROFILE.create_record(_record_columns(), ExampleRecord)


def test_model_constructor_accepts_raw_row_with_schema_fields():
    tag = DEFAULT_SCHEMA_PROFILE.create_record(
        {**_record_columns(), "ZNAME6": "tax", "ZUSER8": 2}, Tag
    )

    assert tag.name == "tax"
    assert tag.user == 2


def test_public_fields_are_assigned_once_without_touching_private_fields():
    converter = Mock(side_effect=str.upper)
    profile = SchemaProfile(
        {
            **DEFAULT_SCHEMA_PROFILE.column_map,
            Tag.__name__: {
                **DEFAULT_SCHEMA_PROFILE.column_map[Tag.__name__],
                **{"name": schema_field("NAME", converter=converter)},
            },
        }
    )
    raw = {**_record_columns(), "NAME": "tax", "ZUSER8": 2}
    tag = profile.create_record(raw, Tag)
    converter.assert_called_once_with("tax")
    assert (tag.id, tag.gid, tag.name, tag.user) == (1, "gid", "TAX", 2)
    assert tag._raw == raw


@pytest.mark.parametrize("raw_type, expected", [(1, "Expenses"), (2, "Income")])
def test_category_type_conversion_runs_after_public_field_assignment(
    raw_type, expected
):
    category = DEFAULT_SCHEMA_PROFILE.create_record(
        {
            **_record_columns(),
            "ZNAME2": "category",
            "ZPARENTCATEGORY": None,
            "ZTYPE2": raw_type,
            "ZUSER3": 2,
        },
        Category,
    )
    assert category.type == expected
    category.validate()
