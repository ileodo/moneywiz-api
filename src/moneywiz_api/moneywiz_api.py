from pathlib import Path
import logging

from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.managers.account_manager import AccountManager
from moneywiz_api.managers.category_manager import CategoryManager
from moneywiz_api.managers.investment_holding_manager import (
    InvestmentHoldingManager,
)
from moneywiz_api.managers.payee_manager import PayeeManager
from moneywiz_api.managers.transaction_manager import TransactionManager
from moneywiz_api.managers.tag_manager import TagManager

logger = logging.getLogger(__name__)


class MoneywizApi:
    def __init__(self, db_file: Path):
        self.accessor = DatabaseAccessor(db_file)
        self.account_manager = AccountManager()
        self.payee_manager = PayeeManager()
        self.category_manager = CategoryManager()
        self.transaction_manager = TransactionManager()
        self.investment_holding_manager = InvestmentHoldingManager()
        self.tag_manager = TagManager()

        self.load()

    def load(self):
        self.account_manager.load(self.accessor)
        self.payee_manager.load(self.accessor)
        self.category_manager.load(self.accessor)
        self.transaction_manager.load(self.accessor)
        self.investment_holding_manager.load(self.accessor)
        self.tag_manager.load(self.accessor)
