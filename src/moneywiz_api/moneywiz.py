"""Explicit, result-based interface for loading a MoneyWiz database."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.managers.account_manager import AccountManager
from moneywiz_api.managers.category_manager import CategoryManager
from moneywiz_api.managers.failed_record import FailedRecord
from moneywiz_api.managers.investment_holding_manager import InvestmentHoldingManager
from moneywiz_api.managers.payee_manager import PayeeManager
from moneywiz_api.managers.tag_manager import TagManager
from moneywiz_api.managers.transaction_manager import TransactionManager
from moneywiz_api.schema.schema_profile import SchemaProfile
from moneywiz_api.schema.schema_profile_resolver import SchemaProfileResolver


@dataclass(frozen=True)
class LoadResult:
    accounts: AccountManager
    payees: PayeeManager
    categories: CategoryManager
    transactions: TransactionManager
    investment_holdings: InvestmentHoldingManager
    tags: TagManager
    failed_records: tuple[FailedRecord, ...]


class MoneyWiz:
    def __init__(self, db_file: Path, schema_profile: SchemaProfile | None = None):
        self.db_file = Path(db_file)
        self.schema_profile = schema_profile

    def load(self, on_error: Literal["collect", "raise"] = "collect") -> LoadResult:
        """Load records, or raise RecordLoadError for the first bad record."""
        if on_error not in ("collect", "raise"):
            raise ValueError(f"Unknown on_error mode: {on_error}")

        profile = self.schema_profile
        if profile is None:
            profile = SchemaProfileResolver(self.db_file).resolve()
        profile.validate()
        accessor = DatabaseAccessor(self.db_file, profile)
        managers = (
            AccountManager(),
            PayeeManager(),
            CategoryManager(),
            TransactionManager(),
            InvestmentHoldingManager(),
            TagManager(),
        )
        for manager in managers:
            manager.load(
                accessor,
                strict=on_error == "raise",
                wrap_errors=on_error == "raise",
            )
        return LoadResult(
            *managers,
            failed_records=tuple(
                failure for manager in managers for failure in manager.failed_records
            ),
        )
