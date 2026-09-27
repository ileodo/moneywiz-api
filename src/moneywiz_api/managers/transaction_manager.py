from datetime import datetime
from dataclasses import replace
from decimal import Decimal
from typing import Dict, List, Tuple, Protocol, cast

from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.managers.record_manager import RecordManager
from moneywiz_api.model.transaction import (
    DepositTransaction,
    InvestmentBuyTransaction,
    InvestmentExchangeTransaction,
    InvestmentSellTransaction,
    ReconcileTransaction,
    RefundTransaction,
    Transaction,
    TransferBudgetTransaction,
    TransferDepositTransaction,
    TransferWithdrawTransaction,
    WithdrawTransaction,
)
from moneywiz_api.read_result import ManagerLoadReport
from moneywiz_api.types import ID


class _AccountTransaction(Protocol):
    account: ID
    datetime: datetime


class TransactionManager(RecordManager[Transaction]):
    def __init__(self) -> None:
        super().__init__()
        self.category_assignment: Dict[ID, List[Tuple[ID, Decimal]]] = {}
        self.refund_maps: Dict[ID, ID] = {}
        self.tags_map: Dict[ID, List[ID]] = {}

    @property
    def ents(self) -> Dict[str, type[Transaction]]:
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

    def _load_in_transaction(self, db_accessor: DatabaseAccessor) -> ManagerLoadReport:
        report = super()._load_in_transaction(db_accessor)
        category_assignment, category_report = db_accessor.read_category_assignments()
        refund_maps, refund_report = db_accessor.read_refund_maps()
        tags_map, tags_report = db_accessor.read_tags_map()
        self.category_assignment = category_assignment
        self.refund_maps = refund_maps
        self.tags_map = tags_map
        return replace(
            report,
            relationships={
                "category_assignments": category_report,
                "refund_links": refund_report,
                "transaction_tags": tags_report,
            },
        )

    def _discard_incomplete_load(self) -> None:
        """Clear records and relationships after an incomplete load."""
        super()._discard_incomplete_load()
        self.category_assignment = {}
        self.refund_maps = {}
        self.tags_map = {}

    def category_for_transaction(
        self, transaction_id: ID
    ) -> List[Tuple[ID, Decimal]] | None:
        return self.category_assignment.get(transaction_id)

    def tags_for_transaction(self, transaction_id: ID) -> List[ID] | None:
        return self.tags_map.get(transaction_id)

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
                and hasattr(x, "account")
                and cast(_AccountTransaction, x).account == account_id
                and x.datetime <= until
            ],
            key=lambda x: x.datetime,
        )

    def get_all(self, until: datetime = datetime.now()) -> List[Transaction]:
        return sorted(
            [
                x
                for _, x in self.records().items()
                if not isinstance(x, TransferBudgetTransaction) and x.datetime <= until
            ],
            key=lambda x: x.datetime,
        )
