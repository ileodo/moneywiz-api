import logging
from pathlib import Path
from typing import Iterable

from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.managers.account_manager import AccountManager
from moneywiz_api.managers.category_manager import CategoryManager
from moneywiz_api.managers.investment_holding_manager import (
    InvestmentHoldingManager,
)
from moneywiz_api.managers.payee_manager import PayeeManager
from moneywiz_api.managers.record_manager import RecordManager
from moneywiz_api.managers.tag_manager import TagManager
from moneywiz_api.managers.transaction_manager import TransactionManager
from moneywiz_api.read_result import ApiCompleteness

logger = logging.getLogger(__name__)


class MoneywizApi:
    def __init__(self, db_file: Path, managers: Iterable[str] | None = None):
        self.accessor = DatabaseAccessor(db_file)
        self.account_manager = AccountManager()
        self.payee_manager = PayeeManager()
        self.category_manager = CategoryManager()
        self.transaction_manager = TransactionManager()
        self.investment_holding_manager = InvestmentHoldingManager()
        self.tag_manager = TagManager()
        self._managers: dict[str, RecordManager] = {
            "accounts": self.account_manager,
            "payees": self.payee_manager,
            "categories": self.category_manager,
            "transactions": self.transaction_manager,
            "investment_holdings": self.investment_holding_manager,
            "tags": self.tag_manager,
        }

        self.load(managers)

    def load(self, managers: Iterable[str] | None = None) -> None:
        """Load requested and previously loaded managers in one read transaction."""
        requested = tuple(self._managers) if managers is None else tuple(managers)
        unknown = [name for name in requested if name not in self._managers]
        if unknown:
            raise ValueError(f"unknown manager names: {', '.join(unknown)}")
        names = tuple(
            name
            for name, manager in self._managers.items()
            if manager.load_report.observed or name in requested
        )
        try:
            with self.accessor.read_transaction():
                for name in names:
                    self._managers[name].load(self.accessor)
        except BaseException:
            for name in names:
                self._managers[name]._discard_incomplete_load()
            raise

    def completeness(self) -> ApiCompleteness:
        """Return completeness evidence without reloading the database."""
        return ApiCompleteness(
            managers={
                name: manager.load_report
                for name, manager in self._managers.items()
                if manager.load_report.observed
            }
        )

    def close(self) -> None:
        """Close the underlying read-only database connection."""
        self.accessor.close()
