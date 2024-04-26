from abc import ABC
from dataclasses import dataclass, field
from decimal import Decimal

from moneywiz_api.types import ID
from moneywiz_api.model.raw_data_handler import RawDataHandler as RDH
from moneywiz_api.model.record import Record


@dataclass
class Account(Record, ABC):
    """
    ENT: 9
    """

    display_order: int = field(repr=False)
    group_id: int = field(repr=False)

    name: str
    currency: str
    opening_balance: Decimal  # might be a tiny number
    info: str
    user: ID

    def __init__(self, row):
        super().__init__(row)
        self.display_order = row["ZDISPLAYORDER"]
        self.group_id = row["ZGROUPID"]

        self.name = row["ZNAME"]
        self.currency = row["ZCURRENCYNAME"]
        self.opening_balance = RDH.get_decimal(row, "ZOPENINGBALANCE")
        self.info = row["ZINFO"]

        self.user = row["ZUSER"]

        # Fixes

        # Validate
        assert self.display_order is not None, self.as_dict()
        assert self.group_id is not None, self.as_dict()
        assert self.name is not None, self.as_dict()
        assert self.currency is not None, self.as_dict()
        assert self.opening_balance is not None, self.as_dict()
        assert self.info is not None, self.as_dict()
        assert self.user is not None, self.as_dict()


@dataclass
class BankChequeAccount(Account):
    """
    ENT: 10
    """

    def __init__(self, row):
        super().__init__(row)


@dataclass
class BankSavingAccount(Account):
    """
    ENT: 11
    """

    def __init__(self, row):
        super().__init__(row)


@dataclass
class CashAccount(Account):
    """
    ENT: 12
    """

    def __init__(self, row):
        super().__init__(row)


@dataclass
class CreditCardAccount(Account):
    """
    ENT: 13
    """

    statement_day: int  # day in the month

    def __init__(self, row):
        super().__init__(row)
        self.statement_day = row["ZSTATEMENTENDDAY"]

        # Validate
        assert self.statement_day is not None


@dataclass
class LoanAccount(CreditCardAccount):
    """
    ENT: 14
    """

    def __init__(self, row):
        super().__init__(row)


@dataclass
class InvestmentAccount(Account):
    """
    ENT: 15
    """

    def __init__(self, row):
        super().__init__(row)


@dataclass
class ForexAccount(InvestmentAccount):
    """
    ENT: 16
    """

    def __init__(self, row):
        super().__init__(row)
