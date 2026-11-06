import logging
from pathlib import Path

from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.managers.account_manager import AccountManager
from moneywiz_api.managers.category_manager import CategoryManager
from moneywiz_api.managers.failed_record import FailedRecord
from moneywiz_api.managers.investment_holding_manager import (
    InvestmentHoldingManager,
)
from moneywiz_api.managers.payee_manager import PayeeManager
from moneywiz_api.managers.tag_manager import TagManager
from moneywiz_api.managers.transaction_manager import TransactionManager
from moneywiz_api.schema.schema_profile import SchemaProfile
from moneywiz_api.schema.schema_profile_resolver import SchemaProfileResolver

logger = logging.getLogger(__name__)


class MoneywizApi:
    def __init__(
        self,
        db_file: Path,
        schema_profile: SchemaProfile | None = None,
        strict: bool = False,
    ):
        self.strict = strict
        if schema_profile is None:
            schema_profile = SchemaProfileResolver(db_file).resolve()
        schema_profile.validate()
        self.accessor = DatabaseAccessor(db_file, schema_profile)
        self.account_manager = AccountManager()
        self.payee_manager = PayeeManager()
        self.category_manager = CategoryManager()
        self.transaction_manager = TransactionManager()
        self.investment_holding_manager = InvestmentHoldingManager()
        self.tag_manager = TagManager()

        self.load()

    def load(self):
        self.account_manager.load(self.accessor, strict=self.strict)
        self.payee_manager.load(self.accessor, strict=self.strict)
        self.category_manager.load(self.accessor, strict=self.strict)
        self.transaction_manager.load(self.accessor, strict=self.strict)
        self.investment_holding_manager.load(self.accessor, strict=self.strict)
        self.tag_manager.load(self.accessor, strict=self.strict)

    @property
    def failed_records(self) -> list[FailedRecord]:
        """Rows that failed conversion or validation in the latest load."""
        return [
            failure
            for manager in (
                self.account_manager,
                self.payee_manager,
                self.category_manager,
                self.transaction_manager,
                self.investment_holding_manager,
                self.tag_manager,
            )
            for failure in manager.failed_records
        ]
