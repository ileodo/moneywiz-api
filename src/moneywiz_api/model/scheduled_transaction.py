import plistlib
from abc import ABC
from dataclasses import dataclass
from typing import Optional

from moneywiz_api.types import ENT_ID, ID
from moneywiz_api.model.record import Record

# from moneywiz_api.utils import get_column_value


@dataclass
class ScheduledTransaction(Record, ABC):

    currency: str
    duration: int
    duration_units: int
    is_repeatable: bool
    executes_count: int
    execute_date: int
    first_execute_date: int
    is_apn_need_update: bool
    updates_count: int
    account: ID
    account_type: ENT_ID
    amount: float
    description: str
    executed_transactions_dates: list[float]
    notes: Optional[str]

    def __init__(self, row):
        super().__init__(row)

        self.currency = self.get_column_value("CURRENCYNAME")
        self.duration = self.get_column_value("DURATION")
        self.duration_units = self.get_column_value("DURATIONUNITS")
        self.is_repeatable = self.get_column_value("ISREPEATABLE")
        self.executes_count = self.get_column_value("EXECUTESCOUNT")
        self.execute_date = self.get_column_value("EXECUTEDATE")
        self.first_execute_date = self.get_column_value("FIRSTEXECUTEDATE")
        self.is_apn_need_update = self.get_column_value("ISAPNNEEDUPDATE")
        self.updates_count = self.get_column_value("UPDATESCOUNT")
        self.account = self.get_column_value("ACCOUNT")
        self.account_type = self.get_column_value("[0-9]_ACCOUNT")
        self.amount = self.get_column_value("AMOUNT")
        self.description = self.get_column_value("DESC")
        self.executed_transactions_dates = []
        self.notes = self.get_column_value("NOTES")

        try:
            dates_plist = plistlib.loads(
                self.get_column_value("EXECUTEDTRANSACTIONSDATESARRAY")
            )
            for o in dates_plist["$objects"]:
                if isinstance(o, dict) and "NS.time" in o:
                    self.executed_transactions_dates.append(o["NS.time"])
        except:
            pass

        # Validate
        assert self.currency is not None
        assert self.duration is not None
        assert self.duration_units is not None
        assert self.is_repeatable is not None
        assert self.executes_count is not None
        assert self.execute_date is not None
        assert self.first_execute_date is not None
        assert self.is_apn_need_update is not None
        assert self.updates_count is not None
        assert self.account is not None
        assert self.account_type is not None
        assert self.amount is not None
        assert self.description is not None
        assert isinstance(self.executed_transactions_dates, list)
        # self.notes can be None


@dataclass
class ScheduledTransactionHandler(ScheduledTransaction):

    def __init__(self, row):
        super().__init__(row)


@dataclass
class ScheduledDepositTransactionHandler(ScheduledTransaction):

    def __init__(self, row):
        super().__init__(row)


@dataclass
class ScheduledTransferTransactionHandler(ScheduledTransaction):

    recipient_account: ID
    recipient_account_type: ENT_ID

    def __init__(self, row):
        super().__init__(row)

        self.recipient_account = self.get_column_value("RECIPIENTACCOUNT")
        self.recipient_account_type = self.get_column_value("[0-9]_RECIPIENTACCOUNT")

        # Validate
        self.recipient_account is not None
        self.recipient_account_type is not None


@dataclass
class ScheduledWithdrawTransactionHandler(ScheduledTransaction):

    def __init__(self, row):
        super().__init__(row)
