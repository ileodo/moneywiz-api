import logging
from pathlib import Path

from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.managers.account_manager import AccountManager
from moneywiz_api.managers.category_manager import CategoryManager
from moneywiz_api.managers.investment_holding_manager import (
    InvestmentHoldingManager,
)
from moneywiz_api.managers.payee_manager import PayeeManager
from moneywiz_api.managers.tag_manager import TagManager
from moneywiz_api.managers.transaction_manager import TransactionManager
from moneywiz_api.schema_profile import SchemaProfile

logger = logging.getLogger(__name__)


class MoneywizApi:
    def __init__(
        self, db_file: Path, schema_profile: SchemaProfile = DEFAULT_SCHEMA_PROFILE
    ):
        self.schema_profile = schema_profile
        self.accessor = DatabaseAccessor(db_file)
        self.account_manager = AccountManager(self.schema_profile)
        self.payee_manager = PayeeManager(self.schema_profile)
        self.category_manager = CategoryManager(self.schema_profile)
        self.transaction_manager = TransactionManager(self.schema_profile)
        self.investment_holding_manager = InvestmentHoldingManager(self.schema_profile)
        self.tag_manager = TagManager(self.schema_profile)

        self.load()

    def load(self):
        self.account_manager.load(self.accessor)
        self.payee_manager.load(self.accessor)
        self.category_manager.load(self.accessor)
        self.transaction_manager.load(self.accessor)
        self.investment_holding_manager.load(self.accessor)
        self.tag_manager.load(self.accessor)
