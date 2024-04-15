from typing import Dict, Callable, List

from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.model.scheduled_transaction import (
    ScheduledTransaction,
    ScheduledDepositTransactionHandler,
    ScheduledTransactionHandler,
    ScheduledTransferTransactionHandler,
    ScheduledWithdrawTransactionHandler,
)
from moneywiz_api.managers.record_manager import RecordManager


class ScheduledTransactionManager(RecordManager[ScheduledTransaction]):
    def __init__(self):
        super().__init__()

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

    def get_all(self) -> List[ScheduledTransaction]:
        return sorted(
            [x for _, x in self.records().items()],
            key=lambda x: x.execute_date,
        )
