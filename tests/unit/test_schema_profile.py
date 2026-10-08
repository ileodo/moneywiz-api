from dataclasses import dataclass
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from moneywiz_api import DEFAULT_SCHEMA_PROFILE, MoneywizApi, SchemaProfile
from moneywiz_api.managers.tag_manager import TagManager
from moneywiz_api.model.account import Account, CreditCardAccount, LoanAccount
from moneywiz_api.model.record import Record
from moneywiz_api.schema.schema_fields import decimal_field, schema_field
from moneywiz_api.model.tag import Tag


def tag_row():
    return {
        "Z_ENT": 1,
        "ZOBJECTCREATIONDATE": 0,
        "ZGID": "gid",
        "Z_PK": 1,
        "ZNAME6": "default",
        "ZUSER8": 2,
        "CUSTOM_NAME": "custom",
    }


def test_profile_injection_is_isolated_and_preserved_through_constructors():
    profile = SchemaProfile(
        {
            **DEFAULT_SCHEMA_PROFILE.column_map,
            Record.__name__: {
                **DEFAULT_SCHEMA_PROFILE.column_map[Record.__name__],
                **{"id": schema_field("CUSTOM_ID")},
            },
            Tag.__name__: {
                **DEFAULT_SCHEMA_PROFILE.column_map[Tag.__name__],
                **{"name": schema_field("CUSTOM_NAME")},
            },
        }
    )
    raw = {**tag_row(), "CUSTOM_ID": 9}
    custom = profile.create_record(raw, Tag)
    default = DEFAULT_SCHEMA_PROFILE.create_record(raw, Tag)
    assert (custom.id, custom.name, custom.user) == (9, "custom", 2)
    assert (default.id, default.name) == (1, "default")
    assert profile.create_record(raw, Tag).name == "custom"


def test_profile_merges_multiple_inheritance_levels_and_converters():
    profile = SchemaProfile(
        {
            **DEFAULT_SCHEMA_PROFILE.column_map,
            Account.__name__: {
                **DEFAULT_SCHEMA_PROFILE.column_map[Account.__name__],
                **{"opening_balance": decimal_field("BALANCE")},
            },
            CreditCardAccount.__name__: {
                **DEFAULT_SCHEMA_PROFILE.column_map[CreditCardAccount.__name__],
                **{"statement_day": schema_field("STATEMENT")},
            },
            LoanAccount.__name__: {
                **DEFAULT_SCHEMA_PROFILE.column_map[LoanAccount.__name__],
                **{"name": schema_field("LOAN_NAME")},
            },
        }
    )
    raw = {
        **tag_row(),
        "ZDISPLAYORDER": 1,
        "ZGROUPID": 1,
        "LOAN_NAME": "loan",
        "ZCURRENCYNAME": "GBP",
        "BALANCE": 12.34,
        "ZINFO": None,
        "ZUSER": 2,
        "STATEMENT": 15,
    }
    loan = profile.create_record(raw, LoanAccount)
    assert loan.name == "loan"
    assert loan.opening_balance == Decimal("12.34")
    assert loan.statement_day == 15
    loan.validate()


def test_complete_profile_and_immutable_definitions():
    definitions = {
        **DEFAULT_SCHEMA_PROFILE.column_map,
        "Record": {**DEFAULT_SCHEMA_PROFILE.column_map["Record"], "id": schema_field("ID")},
    }
    profile = SchemaProfile(definitions)
    definitions["Record"].clear()
    row = {**tag_row(), "ID": 3}
    record = profile.create_record(row, Record)
    assert record.id == 3
    with pytest.raises(RuntimeError, match="name: Could not resolve field name"):
        DEFAULT_SCHEMA_PROFILE.create_record({"Z_PK": 1}, Tag)
    with pytest.raises(TypeError):
        profile.column_map["Record"]["id"] = schema_field("OTHER")


def test_manager_uses_injected_profile():
    profile = SchemaProfile(
        {
            **DEFAULT_SCHEMA_PROFILE.column_map,
            Tag.__name__: {
                **DEFAULT_SCHEMA_PROFILE.column_map[Tag.__name__],
                **{"name": schema_field("CUSTOM_NAME")},
            },
        }
    )
    accessor = Mock()
    accessor.schema_profile = profile
    accessor.query_objects.return_value = [tag_row()]
    accessor.typename_for.return_value = "Tag"
    manager = TagManager()
    manager.load(accessor)
    assert manager.get(1).name == "custom"


def test_api_resolves_profile_from_database_path():
    with (
        patch("moneywiz_api.moneywiz_api.SchemaProfileResolver") as resolver_cls,
        patch("moneywiz_api.moneywiz_api.DatabaseAccessor") as accessor_cls,
        patch.object(MoneywizApi, "load"),
    ):
        resolver_cls.return_value.resolve.return_value = DEFAULT_SCHEMA_PROFILE
        api = MoneywizApi("unused.sqlite")

    resolver_cls.assert_called_once_with("unused.sqlite")
    resolver_cls.return_value.resolve.assert_called_once_with()
    accessor_cls.assert_called_once_with("unused.sqlite", DEFAULT_SCHEMA_PROFILE)
    assert api.accessor is accessor_cls.return_value


def test_default_profile_is_valid_for_all_record_models():
    DEFAULT_SCHEMA_PROFILE.validate()


def test_validation_reports_missing_public_and_inherited_fields():
    profile = SchemaProfile({Tag: {"name": schema_field("NAME")}})
    with pytest.raises(ValueError) as error:
        profile.validate([Tag])
    assert str(error.value) == (
        "Missing schema field definitions: Tag.gid, Tag.id, Tag.user"
    )


def test_validation_accepts_inherited_definitions_and_ignores_private_fields():
    profile = SchemaProfile(
        {
            Record: {"gid": schema_field("GID"), "id": schema_field("ID")},
            Account: {
                name: schema_field(name)
                for name in (
                    "display_order",
                    "group_id",
                    "name",
                    "currency",
                    "opening_balance",
                    "info",
                    "user",
                )
            },
            CreditCardAccount: {"statement_day": schema_field("STATEMENT")},
        }
    )
    profile.validate([LoanAccount])


def test_validation_discovers_application_record_subclasses():
    @dataclass
    class CustomRecord(Record):
        custom_value: str
        _private_value: str

    with pytest.raises(ValueError, match="CustomRecord.custom_value"):
        DEFAULT_SCHEMA_PROFILE.validate()
    profile = SchemaProfile(
        {
            **DEFAULT_SCHEMA_PROFILE.column_map,
            CustomRecord.__name__: {"custom_value": schema_field("CUSTOM_VALUE")},
        }
    )
    profile.validate()
