from datetime import datetime
from typing import Dict, Callable, List, Tuple

from moneywiz_api import utils
from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.model.transaction import (
    Transaction,
    DepositTransaction,
    InvestmentExchangeTransaction,
    InvestmentBuyTransaction,
    InvestmentSellTransaction,
    ReconcileTransaction,
    RefundTransaction,
    TransferBudgetTransaction,
    TransferDepositTransaction,
    TransferWithdrawTransaction,
    WithdrawTransaction,
)
from moneywiz_api.managers.record_manager import RecordManager
from moneywiz_api.types import ID


class TransactionManager(RecordManager[Transaction]):
    def __init__(self):
        super().__init__()
        self.category_assignment: Dict[ID, List[Tuple[ID, float]]] = {}
        self.refund_maps: Dict[ID, ID] = {}

    @property
    def ents(self) -> Dict[str, Callable]:
        return {
            "DepositTransaction": DepositTransaction,
            "InvestmentExchangeTransaction": InvestmentExchangeTransaction,
            "InvestmentBuyTransaction": InvestmentBuyTransaction,
            "InvestmentSellTransaction": InvestmentSellTransaction,
            "ReconcileTransaction": ReconcileTransaction,
            "RefundTransaction": RefundTransaction,
            "TransferBudgetTransaction": TransferBudgetTransaction,
            "TransferDepositTransaction": TransferDepositTransaction,
            "TransferWithdrawTransaction": TransferWithdrawTransaction,
            "WithdrawTransaction": WithdrawTransaction,
        }

    def load(self, db_accessor: DatabaseAccessor) -> None:
        super().load(db_accessor)
        self.category_assignment: Dict[
            ID, List[Tuple[ID, float]]
        ] = db_accessor.get_category_assignment()
        self.refund_maps: Dict[ID, ID] = db_accessor.get_refund_maps()

    def category_for_transaction(
        self, transaction_id: ID
    ) -> List[Tuple[ID, float]] | None:
        return self.category_assignment.get(transaction_id)

    def original_transaction_for_refund_transaction(
        self, transaction_id: ID
    ) -> ID | None:
        return self.refund_maps.get(transaction_id)

    def get_all_for_account(
        self, account_id: ID, until: datetime = datetime.now()
    ) -> List[Transaction]:
        """
        Get all transactions for a given account
        :param account_id:
        :param until: inclusive
        :return:
        """
        return sorted(
            [
                x
                for _, x in self.records().items()
                if not isinstance(x, TransferBudgetTransaction)
                and x.account == account_id
                and x.date <= utils.get_date(until)
            ],
            key=lambda x: x.date,
        )

    def get_all(self, until: datetime = datetime.now()) -> List[Transaction]:
        return sorted(
            [
                x
                for _, x in self.records().items()
                if not isinstance(x, TransferBudgetTransaction)
                and x.date <= utils.get_date(until)
            ],
            key=lambda x: x.date,
        )
