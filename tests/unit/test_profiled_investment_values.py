import sqlite3
from decimal import Decimal
from typing import cast
from unittest.mock import Mock, patch

import pytest

from moneywiz_api import (
    DEFAULT_SCHEMA_PROFILE,
    MoneywizApi,
    SchemaProfile,
    SchemaProfileResolver,
)
from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.managers.investment_holding_manager import InvestmentHoldingManager
from moneywiz_api.managers.transaction_manager import TransactionManager
from moneywiz_api.model.investment_holding import InvestmentHolding
from moneywiz_api.model.transaction import (
    InvestmentBuyTransaction,
    InvestmentSellTransaction,
)
from moneywiz_api.schema.schema_fields import (
    decimal_field,
    nullable_decimal_field,
    schema_field,
)
from moneywiz_api.schema.schema_profile_resolver import UnsupportedInvestmentSchemaError


def investment_profile(holding_shares, transaction_shares, price):
    definitions = {
        name: dict(fields) for name, fields in DEFAULT_SCHEMA_PROFILE.column_map.items()
    }
    definitions["InvestmentHolding"]["number_of_shares"] = nullable_decimal_field(
        holding_shares
    )
    for model in ("InvestmentBuyTransaction", "InvestmentSellTransaction"):
        definitions[model]["number_of_shares"] = decimal_field(transaction_shares)
        definitions[model]["price_per_share"] = decimal_field(price)
    return SchemaProfile(definitions)


UNSUFFIXED_PROFILE = investment_profile(
    "ZNUMBEROFSHARES", "ZNUMBEROFSHARES", "ZPRICEPERSHARE"
)
MIXED_PROFILE = investment_profile(
    "ZNUMBEROFSHARES", "ZNUMBEROFSHARES1", "ZPRICEPERSHARE1"
)


def investment_transaction_row(ent: int, amount: float) -> dict:
    return {
        "Z_ENT": ent,
        "ZOBJECTCREATIONDATE": 0.0,
        "ZGID": f"investment-{ent}",
        "Z_PK": ent,
        "ZRECONCILED": 0,
        "ZAMOUNT1": amount,
        "ZDESC2": "Investment",
        "ZDATE1": 0.0,
        "ZNOTES1": None,
        "ZACCOUNT2": 1,
        "ZFEE2": 0.0,
        "ZINVESTMENTHOLDING": 24,
        "ZNUMBEROFSHARES": 2.0,
        "ZNUMBEROFSHARES1": 9.0,
        "ZPRICEPERSHARE": 10.0,
        "ZPRICEPERSHARE1": 1.0,
    }


def investment_holding_row() -> dict:
    return {
        "Z_ENT": 24,
        "ZOBJECTCREATIONDATE": 0.0,
        "ZGID": "holding",
        "Z_PK": 24,
        "ZINVESTMENTACCOUNT": 1,
        "ZOPENNINGNUMBEROFSHARES": None,
        "ZNUMBEROFSHARES": 2.0,
        "ZNUMBEROFSHARES1": 9.0,
        "ZSYMBOL": "ACME",
        "ZHOLDINGTYPE": None,
        "ZDESC": "Acme Corp.",
        "ZISPRICEPERSHAREAVAILABLEONLINE": 0,
    }


@pytest.mark.parametrize(
    ("constructor", "row"),
    [
        (InvestmentBuyTransaction, investment_transaction_row(40, -20.0)),
        (InvestmentSellTransaction, investment_transaction_row(41, 20.0)),
    ],
)
def test_transactions_use_selected_profile_alias(constructor, row) -> None:
    transaction = UNSUFFIXED_PROFILE.create_record(row, constructor)

    assert transaction.number_of_shares == Decimal("2.0")
    assert transaction.price_per_share == Decimal("10.0")


def test_holding_uses_selected_profile_alias() -> None:
    holding = UNSUFFIXED_PROFILE.create_record(
        investment_holding_row(), InvestmentHolding
    )

    assert holding.number_of_shares == Decimal("2.0")


@pytest.mark.parametrize(
    ("constructor", "row"),
    [
        (InvestmentBuyTransaction, investment_transaction_row(40, -9.0)),
        (InvestmentSellTransaction, investment_transaction_row(41, 9.0)),
    ],
)
def test_mixed_profile_uses_consumer_specific_share_aliases(constructor, row) -> None:
    transaction = MIXED_PROFILE.create_record(row, constructor)
    holding = MIXED_PROFILE.create_record(investment_holding_row(), InvestmentHolding)

    assert transaction.number_of_shares == Decimal("9.0")
    assert transaction.price_per_share == Decimal("1.0")
    assert holding.number_of_shares == Decimal("2.0")


@pytest.mark.parametrize(
    ("constructor", "row"),
    [
        (InvestmentBuyTransaction, investment_transaction_row(40, -20.0)),
        (InvestmentSellTransaction, investment_transaction_row(41, 20.0)),
    ],
)
def test_observed_store_profile_uses_suffixed_transaction_price(
    constructor, row
) -> None:
    transaction = DEFAULT_SCHEMA_PROFILE.create_record(row, constructor)

    assert transaction.number_of_shares == Decimal("2.0")
    assert transaction.price_per_share == Decimal("1.0")


def create_investment_database(db_path, rows):
    columns = sorted({column for row in rows for column in row})
    column_sql = ", ".join(f'"{column}"' for column in columns)
    placeholders = ", ".join("?" for _ in columns)
    with sqlite3.connect(db_path) as connection:
        connection.execute(f"CREATE TABLE ZSYNCOBJECT ({column_sql})")
        connection.executemany(
            f"INSERT INTO ZSYNCOBJECT VALUES ({placeholders})",
            [[row.get(column) for column in columns] for row in rows],
        )
        connection.execute("CREATE TABLE Z_PRIMARYKEY (Z_ENT INTEGER, Z_NAME TEXT)")
        connection.executemany(
            "INSERT INTO Z_PRIMARYKEY VALUES (?, ?)",
            [
                (24, "InvestmentHolding"),
                (40, "InvestmentBuyTransaction"),
                (41, "InvestmentSellTransaction"),
            ]
            + [
                (100 + index, name)
                for index, name in enumerate(TransactionManager().ents)
                if name not in {"InvestmentBuyTransaction", "InvestmentSellTransaction"}
            ],
        )
        connection.execute(
            "CREATE TABLE Z_37TAGS (Z_3TRANSACTIONS INTEGER, Z_4TAGS INTEGER)"
        )
    connection.close()


@pytest.mark.parametrize(
    ("holding_shares", "transaction_shares", "price"),
    [
        ("ZNUMBEROFSHARES", "ZNUMBEROFSHARES", "ZPRICEPERSHARE"),
        ("ZNUMBEROFSHARES", "ZNUMBEROFSHARES1", "ZPRICEPERSHARE1"),
        ("ZNUMBEROFSHARES", "ZNUMBEROFSHARES", "ZPRICEPERSHARE1"),
        ("ZNUMBEROFSHARES1", "ZNUMBEROFSHARES1", "ZPRICEPERSHARE1"),
    ],
)
def test_managers_and_direct_reads_use_same_resolved_profile(
    tmp_path, holding_shares, transaction_shares, price
) -> None:
    rows = [
        investment_holding_row(),
        investment_transaction_row(40, -20.0),
        investment_transaction_row(41, 20.0),
    ]
    for row in rows:
        for column in (
            "ZNUMBEROFSHARES",
            "ZNUMBEROFSHARES1",
            "ZPRICEPERSHARE",
            "ZPRICEPERSHARE1",
        ):
            row[column] = None
        row[holding_shares if row["Z_ENT"] == 24 else transaction_shares] = 2.0
        if row["Z_ENT"] != 24:
            row[price] = 10.0
    db_path = tmp_path / "moneywiz.sqlite"
    create_investment_database(db_path, rows)
    profile = SchemaProfileResolver(db_path).resolve()
    accessor = DatabaseAccessor(db_path, profile)
    try:
        transaction_manager = TransactionManager()
        transaction_manager.load(accessor)
        holding_manager = InvestmentHoldingManager()
        holding_manager.load(accessor)

        for pk, constructor in (
            (40, InvestmentBuyTransaction),
            (41, InvestmentSellTransaction),
        ):
            loaded = transaction_manager.get(pk)
            direct = accessor.get_record(pk, constructor)
            by_gid = accessor.get_record_by_gid(f"investment-{pk}", constructor)
            assert loaded == direct == by_gid
            assert direct.number_of_shares == Decimal("2.0")
            assert direct.price_per_share == Decimal("10.0")
        holding = accessor.get_record(24, InvestmentHolding)
        assert holding_manager.get(24) == holding
        assert holding.number_of_shares == Decimal("2.0")
        assert accessor.schema_profile is profile
        assert transaction_manager.load_errors == holding_manager.load_errors == []
    finally:
        accessor._con.close()


class ManagerAccessor:
    schema_profile = UNSUFFIXED_PROFILE

    def __init__(self, typename, rows):
        self.typename = typename
        self.rows = rows

    def query_objects(self, _typenames):
        return self.rows

    def typename_for(self, _ent_id):
        return self.typename

    def get_category_assignment(self):
        return {}

    def get_refund_maps(self):
        return {}

    def get_tags_map(self):
        return {}


@pytest.mark.parametrize("malformation", ["invalid", "null", "missing", "identity"])
def test_managers_report_bad_rows_and_load_later_valid_rows(malformation) -> None:
    bad_row = investment_transaction_row(40, -20.0)
    if malformation == "missing":
        del bad_row["ZPRICEPERSHARE"]
    elif malformation == "identity":
        bad_row["ZGID"] = None
    else:
        bad_row["ZPRICEPERSHARE"] = None if malformation == "null" else "invalid"
    good_row = {**investment_transaction_row(40, -20.0), "Z_PK": 42, "ZGID": "valid"}
    manager = TransactionManager()

    manager.load(
        cast(
            DatabaseAccessor,
            ManagerAccessor("InvestmentBuyTransaction", [bad_row, good_row]),
        )
    )

    assert list(manager.records()) == [42]
    error_type = "AssertionError" if malformation == "identity" else "RuntimeError"
    assert manager.load_errors == [(40, "InvestmentBuyTransaction", error_type)]
    manager.load_errors.clear()
    assert len(manager.load_errors) == 1


@pytest.mark.parametrize("identity", ["gid", "id", "both"])
def test_manager_duplicate_refusal_preserves_existing_records(identity) -> None:
    manager = TransactionManager()
    row = investment_transaction_row(40, -20.0)
    first = UNSUFFIXED_PROFILE.create_record(row, InvestmentBuyTransaction)
    manager.add(first)
    duplicate_row = {
        **row,
        "Z_PK": 41 if identity == "gid" else 40,
        "ZGID": "duplicate" if identity == "id" else row["ZGID"],
    }
    duplicate = UNSUFFIXED_PROFILE.create_record(
        duplicate_row, InvestmentBuyTransaction
    )

    with pytest.raises(RuntimeError, match="Duplicate"):
        manager.add(duplicate)

    assert list(manager.records()) == [40]
    assert manager.get(40) is first
    assert manager.get_by_gid(row["ZGID"]) is first
    assert manager.get_by_gid("duplicate") is None
    assert manager.load_errors == []


@pytest.mark.parametrize("identity", ["gid", "id", "both"])
def test_manager_reports_duplicates_and_loads_later_rows(tmp_path, identity) -> None:
    first_row = investment_transaction_row(40, -20.0)
    first_row["ZNUMBEROFSHARES1"] = None
    first_row["ZPRICEPERSHARE1"] = None
    duplicate_row = {
        **first_row,
        "Z_PK": 41 if identity == "gid" else 40,
        "ZGID": "duplicate" if identity == "id" else first_row["ZGID"],
        "ZAMOUNT1": -40.0,
        "ZNUMBEROFSHARES": 4.0,
    }
    later_row = {**first_row, "Z_PK": 42, "ZGID": "later"}
    db_path = tmp_path / "moneywiz.sqlite"
    create_investment_database(db_path, [first_row, duplicate_row, later_row])
    profile = SchemaProfileResolver(db_path, UNSUFFIXED_PROFILE).resolve()
    accessor = DatabaseAccessor(db_path, profile)
    manager = TransactionManager()

    try:
        manager.load(accessor)

        assert list(manager.records()) == [40, 42]
        first = manager.get(40)
        assert first is not None
        assert manager.get_by_gid(first_row["ZGID"]) is first
        assert first.amount == Decimal("-20.0")
        assert manager.get_by_gid("later") is manager.get(42)
        assert manager.get_by_gid("duplicate") is None
        assert manager.load_errors == [
            (duplicate_row["Z_PK"], "InvestmentBuyTransaction", "RuntimeError")
        ]
        assert (
            manager.category_assignment == manager.refund_maps == manager.tags_map == {}
        )
    finally:
        accessor._con.close()


def test_ambiguous_store_schema_stops_before_record_loading(tmp_path) -> None:
    db_path = tmp_path / "moneywiz.sqlite"
    create_investment_database(db_path, [investment_transaction_row(40, -20.0)])

    with patch("moneywiz_api.moneywiz_api.DatabaseAccessor") as accessor:
        with pytest.raises(UnsupportedInvestmentSchemaError):
            MoneywizApi(db_path)
        accessor.assert_not_called()


def test_manager_does_not_skip_unsupported_schema_errors() -> None:
    accessor = Mock()
    accessor.query_objects.return_value = [investment_transaction_row(40, -20.0)]
    accessor.typename_for.return_value = "InvestmentBuyTransaction"
    accessor.schema_profile.create_record.side_effect = (
        UnsupportedInvestmentSchemaError("unsupported schema")
    )
    manager = TransactionManager()

    with pytest.raises(UnsupportedInvestmentSchemaError):
        manager.load(accessor)
    assert manager.load_errors == []


def default_investment_rows():
    rows = [
        investment_holding_row(),
        investment_transaction_row(40, -20.0),
        investment_transaction_row(41, 20.0),
    ]
    for row in rows:
        row["ZNUMBEROFSHARES1"] = None
        row["ZPRICEPERSHARE"] = None
        if row["Z_ENT"] != 24:
            row["ZPRICEPERSHARE1"] = 10.0
    return rows


@pytest.mark.parametrize(
    ("model", "field_name"),
    [
        (InvestmentHolding, "number_of_shares"),
        (InvestmentBuyTransaction, "number_of_shares"),
        (InvestmentSellTransaction, "number_of_shares"),
        (InvestmentBuyTransaction, "price_per_share"),
        (InvestmentSellTransaction, "price_per_share"),
    ],
)
def test_resolver_preserves_custom_investment_aliases(tmp_path, model, field_name):
    definitions = {
        name: dict(fields) for name, fields in DEFAULT_SCHEMA_PROFILE.column_map.items()
    }
    spec = DEFAULT_SCHEMA_PROFILE.specs_for(model)[field_name]
    definitions[model.__name__][field_name] = schema_field(
        "CUSTOM_FIELD", converter=spec.converter
    )
    rows = default_investment_rows()
    entity = {
        InvestmentHolding: 24,
        InvestmentBuyTransaction: 40,
        InvestmentSellTransaction: 41,
    }[model]
    row = next(row for row in rows if row["Z_ENT"] == entity)
    row["CUSTOM_FIELD"] = 7.0 if field_name == "number_of_shares" else 12.0
    # Ambiguous stock aliases on the customized consumer cannot override its mapping
    # or invalidate inference for the other consumer.
    row[
        "ZNUMBEROFSHARES1" if field_name == "number_of_shares" else "ZPRICEPERSHARE"
    ] = 9.0
    if entity != 24:
        amount = 70.0 if field_name == "number_of_shares" else 24.0
        row["ZAMOUNT1"] = -amount if entity == 40 else amount
    db_path = tmp_path / "moneywiz.sqlite"
    create_investment_database(db_path, rows)
    baseline = SchemaProfile(definitions)

    profile = SchemaProfileResolver(db_path, baseline).resolve()
    record = profile.create_record(row, model)
    record.validate()

    assert getattr(record, field_name) == Decimal(str(row["CUSTOM_FIELD"]))
    assert profile.specs_for(model)[field_name].aliases == ("CUSTOM_FIELD",)
    assert profile.specs_for(model)[field_name].converter is spec.converter
    assert baseline.column_map == definitions


@pytest.mark.parametrize("custom_aliases", [False, True])
def test_resolver_preserves_inherited_investment_fields(tmp_path, custom_aliases):
    definitions = {
        name: dict(fields) for name, fields in DEFAULT_SCHEMA_PROFILE.column_map.items()
    }
    definitions["InvestmentTransaction"] = definitions["InvestmentBuyTransaction"]
    definitions["InvestmentBuyTransaction"] = {}
    definitions["InvestmentSellTransaction"] = {}
    if custom_aliases:
        definitions["InvestmentTransaction"]["number_of_shares"] = decimal_field(
            "CUSTOM_SHARES"
        )
        definitions["InvestmentTransaction"]["price_per_share"] = decimal_field(
            "CUSTOM_PRICE"
        )
    rows = default_investment_rows()
    for row in rows[1:]:
        row["CUSTOM_SHARES"] = 2.0
        row["CUSTOM_PRICE"] = 10.0
        row["ZNUMBEROFSHARES"] = None
        row["ZNUMBEROFSHARES1"] = 2.0
        row["ZPRICEPERSHARE"] = 10.0
        row["ZPRICEPERSHARE1"] = None
    db_path = tmp_path / "moneywiz.sqlite"
    create_investment_database(db_path, rows)
    baseline = SchemaProfile(definitions)

    profile = SchemaProfileResolver(db_path, baseline).resolve()

    for row, model in zip(
        rows[1:], (InvestmentBuyTransaction, InvestmentSellTransaction)
    ):
        record = profile.create_record(row, model)
        record.validate()
        assert record.number_of_shares == Decimal("2.0")
        assert record.price_per_share == Decimal("10.0")
    assert baseline.column_map == definitions


def test_unrelated_custom_mapping_keeps_investment_detection_and_converter(tmp_path):
    definitions = {
        name: dict(fields) for name, fields in DEFAULT_SCHEMA_PROFILE.column_map.items()
    }
    definitions["Tag"]["name"] = schema_field("CUSTOM_TAG_NAME")

    def converter(value):
        return Decimal(str(value))

    definitions["InvestmentBuyTransaction"]["price_per_share"] = schema_field(
        "ZPRICEPERSHARE1", converter=converter
    )
    rows = default_investment_rows()
    for row in rows[1:]:
        row["ZPRICEPERSHARE"] = 10.0
        row["ZPRICEPERSHARE1"] = None
    db_path = tmp_path / "moneywiz.sqlite"
    create_investment_database(db_path, rows)

    profile = SchemaProfileResolver(db_path, SchemaProfile(definitions)).resolve()
    record = profile.create_record(rows[1], InvestmentBuyTransaction)
    record.validate()

    assert record.price_per_share == Decimal("10.0")
    assert (
        profile.specs_for(InvestmentBuyTransaction)["price_per_share"].converter
        is converter
    )
    assert profile.column_map["Tag"]["name"].aliases == ("CUSTOM_TAG_NAME",)


def test_custom_price_does_not_require_stock_price_columns(tmp_path):
    definitions = {
        name: dict(fields) for name, fields in DEFAULT_SCHEMA_PROFILE.column_map.items()
    }
    definitions["InvestmentBuyTransaction"]["price_per_share"] = decimal_field(
        "CUSTOM_PRICE"
    )
    row = investment_transaction_row(40, -24.0)
    row["ZNUMBEROFSHARES1"] = None
    row["CUSTOM_PRICE"] = 12.0
    del row["ZPRICEPERSHARE"]
    del row["ZPRICEPERSHARE1"]
    db_path = tmp_path / "moneywiz.sqlite"
    create_investment_database(db_path, [row])

    profile = SchemaProfileResolver(db_path, SchemaProfile(definitions)).resolve()
    record = profile.create_record(row, InvestmentBuyTransaction)
    record.validate()
    assert record.price_per_share == Decimal("12.0")


def test_custom_price_does_not_bypass_ambiguous_default_shares(tmp_path):
    definitions = {
        name: dict(fields) for name, fields in DEFAULT_SCHEMA_PROFILE.column_map.items()
    }
    definitions["InvestmentBuyTransaction"]["price_per_share"] = decimal_field(
        "CUSTOM_PRICE"
    )
    row = {**investment_transaction_row(40, -24.0), "CUSTOM_PRICE": 12.0}
    db_path = tmp_path / "moneywiz.sqlite"
    create_investment_database(db_path, [row])

    with pytest.raises(UnsupportedInvestmentSchemaError):
        SchemaProfileResolver(db_path, SchemaProfile(definitions)).resolve()
