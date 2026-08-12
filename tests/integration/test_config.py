import os
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from moneywiz_api.types import ID


def get_test_db_path() -> Path:
    test_db_path = os.environ.get("MONEYWIZ_TEST_DB_PATH")
    if test_db_path is None:
        raise pytest.UsageError(
            "integration tests require MONEYWIZ_TEST_DB_PATH to reference a test database"
        )

    db_path = Path(test_db_path).expanduser().resolve()
    if not db_path.is_file():
        raise pytest.UsageError(
            f"MONEYWIZ_TEST_DB_PATH does not exist or is not a file: {db_path}"
        )

    try:
        with sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True) as connection:
            has_primary_key = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'Z_PRIMARYKEY'"
            ).fetchone()
    except sqlite3.DatabaseError as exc:
        raise pytest.UsageError(
            f"MONEYWIZ_TEST_DB_PATH is not a readable SQLite database: {db_path}"
        ) from exc

    if has_primary_key is None:
        raise pytest.UsageError(
            f"MONEYWIZ_TEST_DB_PATH is not a MoneyWiz database: {db_path}"
        )

    return db_path


BALANCE_AS_OF_DATE = datetime(2025, 1, 1, 0, 0, 0)

# The integration suite accepts any disposable MoneyWiz database. Fixture-specific
# balance expectations are deliberately opt-in rather than assuming private IDs.
CASH_BALANCES: list[tuple[ID, Decimal]] = []
HOLDINGS_BALANCES: list[tuple[ID, dict[ID, Decimal]]] = []
