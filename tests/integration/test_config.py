import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

_test_db_path = os.environ.get("MONEYWIZ_TEST_DB_PATH")
if _test_db_path is None:
    pytest.skip(
        "integration tests require MONEYWIZ_TEST_DB_PATH to reference a test database",
        allow_module_level=True,
    )

TEST_DB_PATH = Path(_test_db_path).expanduser().resolve()
if not TEST_DB_PATH.is_file():
    raise pytest.UsageError(
        f"MONEYWIZ_TEST_DB_PATH does not exist or is not a file: {TEST_DB_PATH}"
    )

try:
    with sqlite3.connect(f"{TEST_DB_PATH.as_uri()}?mode=ro", uri=True) as connection:
        has_primary_key = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'Z_PRIMARYKEY'"
        ).fetchone()
except sqlite3.DatabaseError as exc:
    raise pytest.UsageError(
        f"MONEYWIZ_TEST_DB_PATH is not a readable SQLite database: {TEST_DB_PATH}"
    ) from exc

if has_primary_key is None:
    raise pytest.UsageError(
        f"MONEYWIZ_TEST_DB_PATH is not a MoneyWiz database: {TEST_DB_PATH}"
    )

BALANCE_AS_OF_DATE = datetime(2023, 5, 19, 0, 0, 0)
CASH_BALANCES = [
    # (ACCOUNT_PK, BALANCE)
    (1001, -100.00),
    (1002, -202.33),
]

HOLDINGS_BALANCES = [
    # (ACCOUNT_PK, {
    #     HOLDINGS_PK: HOLDINGS_BALANCE)
    # })
    (
        2001,
        {
            3001: 15,
        },
    ),
]
