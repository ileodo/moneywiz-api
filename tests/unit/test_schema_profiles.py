import sqlite3

from moneywiz_api.model.raw_data_handler import RawDataHandler
from moneywiz_api.schema_profile import detect_schema_profile


def make_connection(*columns: str) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    column_sql = ", ".join(f'"{column}" FLOAT' for column in columns)
    connection.execute(
        f"CREATE TABLE ZSYNCOBJECT (Z_PK INTEGER, Z_ENT INTEGER, {column_sql})"
    )
    return connection


def add_investment_entities(connection: sqlite3.Connection) -> None:
    connection.execute("CREATE TABLE Z_PRIMARYKEY (Z_ENT INTEGER, Z_NAME TEXT)")
    connection.executemany(
        "INSERT INTO Z_PRIMARYKEY VALUES (?, ?)",
        [
            (24, "InvestmentHolding"),
            (40, "InvestmentBuyTransaction"),
            (41, "InvestmentSellTransaction"),
        ],
    )


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


def test_detects_suffixed_fixture_profile() -> None:
    connection = make_connection("ZNUMBEROFSHARES1", "ZPRICEPERSHARE1")

    profile = detect_schema_profile(connection)

    assert profile.profile_id == "suffixed-investment-columns"
    assert profile.holding_number_of_shares_column == "ZNUMBEROFSHARES1"
    assert profile.transaction_number_of_shares_column == "ZNUMBEROFSHARES1"
    assert profile.price_per_share_column == "ZPRICEPERSHARE1"


def test_detects_unsuffixed_profile_when_aliases_are_absent() -> None:
    connection = make_connection("ZNUMBEROFSHARES", "ZPRICEPERSHARE")

    profile = detect_schema_profile(connection)

    assert profile.profile_id == "unsuffixed-investment-columns"
    assert profile.holding_number_of_shares_column == "ZNUMBEROFSHARES"
    assert profile.transaction_number_of_shares_column == "ZNUMBEROFSHARES"
    assert profile.price_per_share_column == "ZPRICEPERSHARE"


def test_detects_mixed_investment_columns() -> None:
    connection = make_connection("ZNUMBEROFSHARES", "ZPRICEPERSHARE1")

    profile = detect_schema_profile(connection)

    assert profile.profile_id == "mixed-investment-columns"
    assert profile.holding_number_of_shares_column == "ZNUMBEROFSHARES"
    assert profile.transaction_number_of_shares_column == "ZNUMBEROFSHARES"
    assert profile.price_per_share_column == "ZPRICEPERSHARE1"


def test_detects_consumer_specific_mixed_share_columns() -> None:
    connection = make_connection(
        "ZNUMBEROFSHARES", "ZNUMBEROFSHARES1", "ZPRICEPERSHARE1"
    )
    add_investment_entities(connection)
    insert_investment_row(connection, 24, ZNUMBEROFSHARES=2.0, ZNUMBEROFSHARES1=None)
    insert_investment_row(connection, 40, ZNUMBEROFSHARES=None, ZNUMBEROFSHARES1=9.0)
    insert_investment_row(connection, 41, ZNUMBEROFSHARES=None, ZNUMBEROFSHARES1=3.0)

    profile = detect_schema_profile(connection)

    assert profile.profile_id == "mixed-investment-columns"
    assert profile.holding_number_of_shares_column == "ZNUMBEROFSHARES"
    assert profile.transaction_number_of_shares_column == "ZNUMBEROFSHARES1"
    assert profile.price_per_share_column == "ZPRICEPERSHARE1"


def test_detects_observed_store_profile_from_entity_rows() -> None:
    connection = make_connection("ZNUMBEROFSHARES", "ZPRICEPERSHARE", "ZPRICEPERSHARE1")
    add_investment_entities(connection)
    insert_investment_row(
        connection,
        24,
        ZNUMBEROFSHARES=None,
        ZPRICEPERSHARE=15.0,
        ZPRICEPERSHARE1=None,
    )
    insert_investment_row(
        connection,
        40,
        ZNUMBEROFSHARES=2.0,
        ZPRICEPERSHARE=None,
        ZPRICEPERSHARE1=10.0,
    )
    insert_investment_row(
        connection,
        41,
        ZNUMBEROFSHARES=3.0,
        ZPRICEPERSHARE=None,
        ZPRICEPERSHARE1=11.0,
    )

    profile = detect_schema_profile(connection)

    assert profile.profile_id == "mixed-investment-columns"
    assert profile.holding_number_of_shares_column == "ZNUMBEROFSHARES"
    assert profile.transaction_number_of_shares_column == "ZNUMBEROFSHARES"
    assert profile.price_per_share_column == "ZPRICEPERSHARE1"


def test_rejects_dual_price_columns_without_discriminating_rows() -> None:
    connection = make_connection("ZNUMBEROFSHARES", "ZPRICEPERSHARE", "ZPRICEPERSHARE1")
    add_investment_entities(connection)
    insert_investment_row(
        connection, 40, ZNUMBEROFSHARES=2.0, ZPRICEPERSHARE=10.0, ZPRICEPERSHARE1=1.0
    )

    profile = detect_schema_profile(connection)

    assert profile.profile_id == "unknown"
    assert not profile.is_known


def test_rejects_ambiguous_investment_column_profile() -> None:
    connection = make_connection(
        "ZNUMBEROFSHARES",
        "ZNUMBEROFSHARES1",
        "ZPRICEPERSHARE",
        "ZPRICEPERSHARE1",
    )

    profile = detect_schema_profile(connection)

    assert profile.profile_id == "unknown"
    assert not profile.is_known


def test_decimal_alias_reads_both_profiles() -> None:
    assert (
        RawDataHandler.get_decimal_alias(
            {"ZNUMBEROFSHARES": 2.5}, "ZNUMBEROFSHARES1", "ZNUMBEROFSHARES"
        )
        == 2.5
    )
    assert (
        RawDataHandler.get_decimal_alias(
            {"ZNUMBEROFSHARES1": 3.5}, "ZNUMBEROFSHARES1", "ZNUMBEROFSHARES"
        )
        == 3.5
    )
    assert (
        RawDataHandler.get_decimal_alias(
            {"ZNUMBEROFSHARES1": None, "ZNUMBEROFSHARES": 4.5},
            "ZNUMBEROFSHARES1",
            "ZNUMBEROFSHARES",
        )
        == 4.5
    )
    assert (
        RawDataHandler.get_nullable_decimal_alias(
            {"ZNUMBEROFSHARES": None}, "ZNUMBEROFSHARES1", "ZNUMBEROFSHARES"
        )
        is None
    )
    assert (
        RawDataHandler.get_nullable_decimal_alias(
            {"ZNUMBEROFSHARES1": None, "ZNUMBEROFSHARES": 5.5},
            "ZNUMBEROFSHARES1",
            "ZNUMBEROFSHARES",
        )
        == 5.5
    )


def test_filter_row_accepts_missing_optional_blob_columns() -> None:
    assert RawDataHandler.filter_row({"Z_PK": 1}) == {"Z_PK": 1}
