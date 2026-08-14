"""Schema capability profiles for MoneyWiz SQLite stores."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


class UnsupportedInvestmentSchemaError(ValueError):
    """Raised when investment column aliases cannot be mapped safely."""


@dataclass(frozen=True)
class SchemaProfile:
    """Capabilities inferred from the physical store schema."""

    profile_id: str
    holding_number_of_shares_column: str | None
    transaction_number_of_shares_column: str | None
    price_per_share_column: str | None

    @property
    def is_known(self) -> bool:
        return self.profile_id != "unknown"

    def require_known(self) -> None:
        """Raise when this profile cannot safely parse investment records."""
        if not self.is_known:
            raise UnsupportedInvestmentSchemaError(
                "unsupported investment schema profile"
            )


def detect_schema_profile(connection: sqlite3.Connection) -> SchemaProfile:
    """Detect a read profile from columns, not from Core Data metadata alone."""
    columns = set()
    for row in connection.execute("PRAGMA table_info(ZSYNCOBJECT)").fetchall():
        columns.add(str(row["name"] if isinstance(row, dict) else row[1]))
    has_suffixed_shares = "ZNUMBEROFSHARES1" in columns
    has_unsuffixed_shares = "ZNUMBEROFSHARES" in columns
    has_suffixed_price = "ZPRICEPERSHARE1" in columns
    has_unsuffixed_price = "ZPRICEPERSHARE" in columns

    if (
        has_suffixed_shares
        and not has_unsuffixed_shares
        and has_suffixed_price
        and not has_unsuffixed_price
    ):
        profile_id = "suffixed-investment-columns"
        holding_number_of_shares_column = "ZNUMBEROFSHARES1"
        transaction_number_of_shares_column = "ZNUMBEROFSHARES1"
        price_per_share_column = "ZPRICEPERSHARE1"
    elif (
        has_unsuffixed_shares
        and not has_suffixed_shares
        and has_unsuffixed_price
        and not has_suffixed_price
    ):
        profile_id = "unsuffixed-investment-columns"
        holding_number_of_shares_column = "ZNUMBEROFSHARES"
        transaction_number_of_shares_column = "ZNUMBEROFSHARES"
        price_per_share_column = "ZPRICEPERSHARE"
    elif (
        has_unsuffixed_shares
        and not has_suffixed_shares
        and has_suffixed_price
        and not has_unsuffixed_price
    ):
        profile_id = "mixed-investment-columns"
        holding_number_of_shares_column = "ZNUMBEROFSHARES"
        transaction_number_of_shares_column = "ZNUMBEROFSHARES"
        price_per_share_column = "ZPRICEPERSHARE1"
    else:
        profile_id = "unknown"
        holding_number_of_shares_column = None
        transaction_number_of_shares_column = None
        price_per_share_column = None

    return SchemaProfile(
        profile_id=profile_id,
        holding_number_of_shares_column=holding_number_of_shares_column,
        transaction_number_of_shares_column=transaction_number_of_shares_column,
        price_per_share_column=price_per_share_column,
    )
