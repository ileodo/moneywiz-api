from dataclasses import dataclass
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from moneywiz_api import DEFAULT_SCHEMA_PROFILE, MoneywizApi, SchemaProfile
from moneywiz_api.managers.tag_manager import TagManager
from moneywiz_api.model.account import Account, CreditCardAccount, LoanAccount
from moneywiz_api.model.record import Record
from moneywiz_api.model.schema_fields import decimal_field, schema_field
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
    custom = Tag(raw, profile)
    default = Tag(raw, DEFAULT_SCHEMA_PROFILE)
    assert (custom.id, custom.name, custom.user) == (9, "custom", 2)
    assert (default.id, default.name) == (1, "default")
    assert Tag(raw, profile).name == "custom"


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
    loan = LoanAccount(raw, profile)
    assert loan.name == "loan"
    assert loan.opening_balance == Decimal("12.34")
    assert loan.statement_day == 15
    loan.validate()


def test_complete_profile_and_immutable_definitions():
    definitions = {"Record": {"id": schema_field("ID")}}
    profile = SchemaProfile(definitions)
    definitions["Record"].clear()
    assert profile.get_field({"ID": 3}, Record, "id") == 3
    with pytest.raises(KeyError):
        profile.get_field(tag_row(), Tag, "name")
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
    accessor.query_objects.return_value = [tag_row()]
    accessor.typename_for.return_value = "Tag"
    manager = TagManager(profile)
    manager.load(accessor)
    assert manager.get(1).name == "custom"


def test_api_passes_profile_to_all_managers():
    profile = SchemaProfile(
        {
            **DEFAULT_SCHEMA_PROFILE.column_map,
            Tag.__name__: {
                **DEFAULT_SCHEMA_PROFILE.column_map[Tag.__name__],
                **{"name": schema_field("CUSTOM_NAME")},
            },
        }
    )
    with (
        patch("moneywiz_api.moneywiz_api.DatabaseAccessor"),
        patch.object(MoneywizApi, "load"),
    ):
        api = MoneywizApi("unused.sqlite", schema_profile=profile)
    for name in (
        "account",
        "category",
        "payee",
        "tag",
        "transaction",
        "investment_holding",
    ):
        assert getattr(api, f"{name}_manager").schema_profile is profile


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
