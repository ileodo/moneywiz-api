"""Schema capability profiles for MoneyWiz SQLite stores."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Iterable


class UnsupportedInvestmentSchemaError(ValueError):
    """Raised when investment column aliases cannot be mapped safely."""


@dataclass(frozen=True)
class SchemaProfile:
    """Capabilities inferred from physical columns and investment rows."""

    profile_id: str
    holding_number_of_shares_column: str | None
    transaction_number_of_shares_column: str | None
    price_per_share_column: str | None

    @property
    def is_known(self) -> bool:
        return self.profile_id != "unknown"

    def require_columns(self, *columns: str) -> None:
        """Raise when this model's profile-selected columns are unresolved."""
        if any(getattr(self, column) is None for column in columns):
            raise UnsupportedInvestmentSchemaError(
                "unsupported investment schema profile"
            )


def _value(row: Any, name: str, index: int) -> Any:
    if isinstance(row, dict):
        return row[name]
    return row[index]


def _column_for_entities(
    connection: sqlite3.Connection,
    columns: set[str],
    unsuffixed_column: str,
    suffixed_column: str,
    entity_names: Iterable[str],
) -> str | None:
    has_unsuffixed = unsuffixed_column in columns
    has_suffixed = suffixed_column in columns
    if has_unsuffixed != has_suffixed:
        return unsuffixed_column if has_unsuffixed else suffixed_column
    if not has_unsuffixed:
        return None

    tables = {
        str(_value(row, "name", 0))
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    if "Z_PRIMARYKEY" not in tables:
        return None

    names = tuple(entity_names)
    placeholders = ", ".join("?" for _ in names)
    entity_rows = connection.execute(
        f'SELECT "Z_ENT", "Z_NAME" FROM "Z_PRIMARYKEY" '
        f'WHERE "Z_NAME" IN ({placeholders})',
        names,
    ).fetchall()
    entity_ids = tuple(_value(row, "Z_ENT", 0) for row in entity_rows)
    if not entity_ids:
        return None

    placeholders = ", ".join("?" for _ in entity_ids)
    counts = connection.execute(
        f'SELECT COUNT("{unsuffixed_column}") AS "unsuffixed_count", '
        f'COUNT("{suffixed_column}") AS "suffixed_count" '
        f'FROM "ZSYNCOBJECT" WHERE "Z_ENT" IN ({placeholders})',
        entity_ids,
    ).fetchone()
    unsuffixed_count = int(_value(counts, "unsuffixed_count", 0))
    suffixed_count = int(_value(counts, "suffixed_count", 1))
    if unsuffixed_count and not suffixed_count:
        return unsuffixed_column
    if suffixed_count and not unsuffixed_count:
        return suffixed_column
    return None


def detect_schema_profile(connection: sqlite3.Connection) -> SchemaProfile:
    """Select investment aliases using columns and entity-specific row evidence."""
    columns = {
        str(_value(row, "name", 1))
        for row in connection.execute("PRAGMA table_info(ZSYNCOBJECT)").fetchall()
    }

    holding_shares = _column_for_entities(
        connection,
        columns,
        "ZNUMBEROFSHARES",
        "ZNUMBEROFSHARES1",
        ("InvestmentHolding",),
    )
    transaction_entities = ("InvestmentBuyTransaction", "InvestmentSellTransaction")
    transaction_shares = _column_for_entities(
        connection,
        columns,
        "ZNUMBEROFSHARES",
        "ZNUMBEROFSHARES1",
        transaction_entities,
    )
    price_per_share = _column_for_entities(
        connection,
        columns,
        "ZPRICEPERSHARE",
        "ZPRICEPERSHARE1",
        transaction_entities,
    )

    if not holding_shares or not transaction_shares or not price_per_share:
        profile_id = "unknown"
    elif (
        len(
            {
                column.endswith("1")
                for column in (holding_shares, transaction_shares, price_per_share)
            }
        )
        > 1
    ):
        profile_id = "mixed-investment-columns"
    elif holding_shares.endswith("1"):
        profile_id = "suffixed-investment-columns"
    else:
        profile_id = "unsuffixed-investment-columns"

    return SchemaProfile(
        profile_id=profile_id,
        holding_number_of_shares_column=holding_shares,
        transaction_number_of_shares_column=transaction_shares,
        price_per_share_column=price_per_share,
    )
