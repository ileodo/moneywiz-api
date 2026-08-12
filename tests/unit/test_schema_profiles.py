import sqlite3

from moneywiz_api.model.raw_data_handler import RawDataHandler
from moneywiz_api.schema_profile import detect_schema_profile


def make_connection(*columns: str) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    column_sql = ", ".join(f'"{column}" FLOAT' for column in columns)
    connection.execute(f"CREATE TABLE ZSYNCOBJECT (Z_PK INTEGER, {column_sql})")
    return connection


def test_detects_suffixed_fixture_profile() -> None:
    connection = make_connection("ZNUMBEROFSHARES1", "ZPRICEPERSHARE1")

    profile = detect_schema_profile(connection)

    assert profile.profile_id == "suffixed-investment-columns"
    assert profile.holding_number_of_shares_column == "ZNUMBEROFSHARES1"
    assert profile.transaction_number_of_shares_column == "ZNUMBEROFSHARES1"
    assert profile.price_per_share_column == "ZPRICEPERSHARE1"


def test_detects_unsuffixed_live_profile() -> None:
    connection = make_connection("ZNUMBEROFSHARES", "ZPRICEPERSHARE", "ZPRICEPERSHARE1")

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

    profile = detect_schema_profile(connection)

    assert profile.profile_id == "mixed-investment-columns"
    assert profile.holding_number_of_shares_column == "ZNUMBEROFSHARES"
    assert profile.transaction_number_of_shares_column == "ZNUMBEROFSHARES1"
    assert profile.price_per_share_column == "ZPRICEPERSHARE1"


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
