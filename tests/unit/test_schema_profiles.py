import sqlite3

import pytest

from moneywiz_api import DEFAULT_SCHEMA_PROFILE, SchemaProfile, SchemaProfileResolver
from moneywiz_api.schema.raw_data_handler import RawDataHandler
from moneywiz_api.schema.schema_profile_resolver import UnsupportedInvestmentSchemaError


def make_connection(db_path, *columns: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    column_sql = ", ".join(f'"{column}" FLOAT' for column in columns)
    connection.execute(
        f"CREATE TABLE ZSYNCOBJECT (Z_PK INTEGER, Z_ENT INTEGER, {column_sql})"
    )
    connection.execute("CREATE TABLE Z_PRIMARYKEY (Z_ENT INTEGER, Z_NAME TEXT)")
    connection.executemany(
        "INSERT INTO Z_PRIMARYKEY VALUES (?, ?)",
        [
            (24, "InvestmentHolding"),
            (40, "InvestmentBuyTransaction"),
            (41, "InvestmentSellTransaction"),
        ],
    )
    connection.execute(
        "CREATE TABLE Z_37TAGS (Z_3TRANSACTIONS INTEGER, Z_4TAGS INTEGER)"
    )
    return connection


def insert_investment_row(
    connection: sqlite3.Connection, entity: int, **values: float | None
) -> None:
    columns = ["Z_ENT", *values]
    placeholders = ", ".join("?" for _ in columns)
    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    connection.execute(
        f"INSERT INTO ZSYNCOBJECT ({quoted_columns}) VALUES ({placeholders})",
        [entity, *values.values()],
    )


def resolve_profile(connection, db_path):
    connection.commit()
    connection.close()
    return SchemaProfileResolver(db_path).resolve()


@pytest.mark.parametrize(
    ("shares_column", "price_column"),
    [
        ("ZNUMBEROFSHARES1", "ZPRICEPERSHARE1"),
        ("ZNUMBEROFSHARES", "ZPRICEPERSHARE"),
        ("ZNUMBEROFSHARES", "ZPRICEPERSHARE1"),
    ],
)
def test_detects_investment_columns_when_aliases_are_absent(
    tmp_path, shares_column, price_column
) -> None:
    db_path = tmp_path / "moneywiz.sqlite"
    connection = make_connection(db_path, shares_column, price_column)
    insert_investment_row(connection, 24, **{shares_column: 2.0})
    for entity in (40, 41):
        insert_investment_row(
            connection, entity, **{shares_column: 2.0, price_column: 10.0}
        )

    profile = resolve_profile(connection, db_path)

    assert profile.column_map["InvestmentHolding"]["number_of_shares"].aliases == (
        shares_column,
    )
    for model in ("InvestmentBuyTransaction", "InvestmentSellTransaction"):
        assert profile.column_map[model]["number_of_shares"].aliases == (shares_column,)
        assert profile.column_map[model]["price_per_share"].aliases == (price_column,)


def test_detects_consumer_specific_mixed_share_columns(tmp_path) -> None:
    db_path = tmp_path / "moneywiz.sqlite"
    connection = make_connection(
        db_path, "ZNUMBEROFSHARES", "ZNUMBEROFSHARES1", "ZPRICEPERSHARE1"
    )
    insert_investment_row(connection, 24, ZNUMBEROFSHARES=2.0, ZNUMBEROFSHARES1=None)
    insert_investment_row(
        connection, 40, ZNUMBEROFSHARES=None, ZNUMBEROFSHARES1=9.0, ZPRICEPERSHARE1=10.0
    )
    insert_investment_row(
        connection, 41, ZNUMBEROFSHARES=None, ZNUMBEROFSHARES1=3.0, ZPRICEPERSHARE1=11.0
    )

    profile = resolve_profile(connection, db_path)

    assert profile.column_map["InvestmentHolding"]["number_of_shares"].aliases == (
        "ZNUMBEROFSHARES",
    )
    for model in ("InvestmentBuyTransaction", "InvestmentSellTransaction"):
        assert profile.column_map[model]["number_of_shares"].aliases == (
            "ZNUMBEROFSHARES1",
        )


def test_detects_observed_store_profile_from_entity_rows(tmp_path) -> None:
    db_path = tmp_path / "moneywiz.sqlite"
    connection = make_connection(
        db_path, "ZNUMBEROFSHARES", "ZPRICEPERSHARE", "ZPRICEPERSHARE1"
    )
    insert_investment_row(
        connection, 24, ZNUMBEROFSHARES=None, ZPRICEPERSHARE=15.0, ZPRICEPERSHARE1=None
    )
    for entity in (40, 41):
        insert_investment_row(
            connection,
            entity,
            ZNUMBEROFSHARES=2.0,
            ZPRICEPERSHARE=None,
            ZPRICEPERSHARE1=10.0,
        )

    profile = resolve_profile(connection, db_path)

    for model in ("InvestmentBuyTransaction", "InvestmentSellTransaction"):
        assert profile.column_map[model]["number_of_shares"].aliases == (
            "ZNUMBEROFSHARES",
        )
        assert profile.column_map[model]["price_per_share"].aliases == (
            "ZPRICEPERSHARE1",
        )


@pytest.mark.parametrize("prices", [(10.0, 1.0), (None, None)])
def test_rejects_dual_price_columns_without_discriminating_rows(
    tmp_path, prices
) -> None:
    db_path = tmp_path / "moneywiz.sqlite"
    connection = make_connection(
        db_path, "ZNUMBEROFSHARES", "ZPRICEPERSHARE", "ZPRICEPERSHARE1"
    )
    insert_investment_row(
        connection,
        40,
        ZNUMBEROFSHARES=2.0,
        ZPRICEPERSHARE=prices[0],
        ZPRICEPERSHARE1=prices[1],
    )

    with pytest.raises(UnsupportedInvestmentSchemaError, match="transaction columns"):
        resolve_profile(connection, db_path)


@pytest.mark.parametrize("shares", [(2.0, 9.0), (None, None)])
def test_rejects_ambiguous_holding_share_columns(tmp_path, shares) -> None:
    db_path = tmp_path / "moneywiz.sqlite"
    connection = make_connection(
        db_path, "ZNUMBEROFSHARES", "ZNUMBEROFSHARES1", "ZPRICEPERSHARE1"
    )
    insert_investment_row(
        connection, 24, ZNUMBEROFSHARES=shares[0], ZNUMBEROFSHARES1=shares[1]
    )

    with pytest.raises(UnsupportedInvestmentSchemaError, match="holding shares column"):
        resolve_profile(connection, db_path)


def test_rejects_conflicting_transaction_column_evidence(tmp_path) -> None:
    db_path = tmp_path / "moneywiz.sqlite"
    connection = make_connection(
        db_path, "ZNUMBEROFSHARES", "ZNUMBEROFSHARES1", "ZPRICEPERSHARE1"
    )
    insert_investment_row(connection, 40, ZNUMBEROFSHARES=2.0, ZPRICEPERSHARE1=10.0)
    insert_investment_row(connection, 41, ZNUMBEROFSHARES1=3.0, ZPRICEPERSHARE1=11.0)

    with pytest.raises(UnsupportedInvestmentSchemaError, match="transaction columns"):
        resolve_profile(connection, db_path)


def test_rejects_missing_investment_columns(tmp_path) -> None:
    db_path = tmp_path / "moneywiz.sqlite"
    connection = make_connection(db_path, "ZNUMBEROFSHARES")
    insert_investment_row(connection, 40, ZNUMBEROFSHARES=2.0)

    with pytest.raises(UnsupportedInvestmentSchemaError, match="transaction columns"):
        resolve_profile(connection, db_path)


def test_empty_investment_entities_do_not_require_row_evidence(tmp_path) -> None:
    db_path = tmp_path / "moneywiz.sqlite"
    connection = make_connection(
        db_path,
        "ZNUMBEROFSHARES",
        "ZNUMBEROFSHARES1",
        "ZPRICEPERSHARE",
        "ZPRICEPERSHARE1",
    )

    profile = resolve_profile(connection, db_path)

    assert profile.column_map == DEFAULT_SCHEMA_PROFILE.column_map
    assert profile.tag_table_info is not None


@pytest.mark.parametrize("entity", [24, 40])
def test_resolves_only_populated_investment_consumers(tmp_path, entity) -> None:
    db_path = tmp_path / "moneywiz.sqlite"
    connection = make_connection(
        db_path,
        "ZNUMBEROFSHARES",
        "ZNUMBEROFSHARES1",
        "ZPRICEPERSHARE",
        "ZPRICEPERSHARE1",
    )
    if entity == 24:
        insert_investment_row(connection, entity, ZNUMBEROFSHARES=0.0)
    else:
        insert_investment_row(
            connection, entity, ZNUMBEROFSHARES1=2.0, ZPRICEPERSHARE1=10.0
        )

    profile = resolve_profile(connection, db_path)

    model = "InvestmentHolding" if entity == 24 else "InvestmentBuyTransaction"
    column = "ZNUMBEROFSHARES" if entity == 24 else "ZNUMBEROFSHARES1"
    assert profile.column_map[model]["number_of_shares"].aliases == (column,)


def test_resolves_investment_fields_with_preconfigured_tag_table(tmp_path) -> None:
    db_path = tmp_path / "moneywiz.sqlite"
    connection = make_connection(db_path, "ZNUMBEROFSHARES1", "ZPRICEPERSHARE")
    insert_investment_row(connection, 40, ZNUMBEROFSHARES1=2.0, ZPRICEPERSHARE=10.0)
    default = resolve_profile(connection, db_path)
    baseline = SchemaProfile(DEFAULT_SCHEMA_PROFILE.column_map, default.tag_table_info)

    profile = SchemaProfileResolver(db_path, baseline).resolve()

    assert profile.tag_table_info == baseline.tag_table_info
    assert profile.column_map["InvestmentBuyTransaction"][
        "number_of_shares"
    ].aliases == ("ZNUMBEROFSHARES1",)
    assert profile.column_map["InvestmentBuyTransaction"][
        "price_per_share"
    ].converter is (
        DEFAULT_SCHEMA_PROFILE.column_map["InvestmentBuyTransaction"][
            "price_per_share"
        ].converter
    )
    assert baseline.column_map == DEFAULT_SCHEMA_PROFILE.column_map


def test_filter_row_accepts_missing_optional_blob_columns() -> None:
    assert RawDataHandler.filter_row({"Z_PK": 1}) == {"Z_PK": 1}
