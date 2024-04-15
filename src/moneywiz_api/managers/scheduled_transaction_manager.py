from datetime import datetime
from typing import Dict, Callable, List, Tuple

from moneywiz_api import utils
from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.model.scheduled_transaction import (
    ScheduledTransaction,
    ScheduledDepositTransactionHandler,
    ScheduledTransactionHandler,
    ScheduledTransferTransactionHandler,
    ScheduledWithdrawTransactionHandler,
)
from moneywiz_api.managers.record_manager import RecordManager
from moneywiz_api.types import ID


class ScheduledTransactionManager(RecordManager[ScheduledTransaction]):
    def __init__(self):
        super().__init__()
        self.category_assignment: Dict[ID, List[Tuple[ID, float]]] = {}
        self.refund_maps: Dict[ID, ID] = {}
        self.tags_map: Dict[ID, ID] = {}

    @property
    def ents(self) -> Dict[str, Callable]:
        return {
            "ScheduledTransactionHandler": ScheduledTransactionHandler,
            "ScheduledDepositTransactionHandler": ScheduledDepositTransactionHandler,
            "ScheduledTransferTransactionHandler": ScheduledTransferTransactionHandler,
            "ScheduledWithdrawTransactionHandler": ScheduledWithdrawTransactionHandler,
        }

    def load(self, db_accessor: DatabaseAccessor) -> None:
        super().load(db_accessor)
        self.category_assignment: Dict[ID, List[Tuple[ID, float]]] = (
            db_accessor.get_category_assignment()
        )
        self.refund_maps: Dict[ID, ID] = db_accessor.get_refund_maps()
        self.tags_map: Dict[ID, ID] = db_accessor.get_tags_map()

    def category_for_transaction(
        self, transaction_id: ID
    ) -> List[Tuple[ID, float]] | None:
        return self.category_assignment.get(transaction_id)

    def tags_for_transaction(self, transaction_id: ID) -> List[ID] | None:
        return self.tags_map.get(transaction_id)

    def original_transaction_for_refund_transaction(
        self, transaction_id: ID
    ) -> ID | None:
        return self.refund_maps.get(transaction_id)

    def get_all(self) -> List[ScheduledTransaction]:
        return sorted(
            [x for _, x in self.records().items()],
            key=lambda x: x.execute_date,
        )
