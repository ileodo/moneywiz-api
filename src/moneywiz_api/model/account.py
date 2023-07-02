from abc import ABC
from dataclasses import dataclass, field

from moneywiz_api.model.record import Record
from moneywiz_api.types import ID


@dataclass
class Account(Record, ABC):
    """
    ENT: 9
    """

    _display_order: int = field(repr=False)
    _group_id: int = field(repr=False)

    name: str
    currency: str
    opening_balance: float
    info: str
    user: ID

    def __init__(self, row):
        super().__init__(row)
        self._display_order = row["ZDISPLAYORDER"]
        self._group_id = row["ZGROUPID"]

        self.name = row["ZNAME"]
        self.currency = row["ZCURRENCYNAME"]
        self.opening_balance = row["ZOPENINGBALANCE"]
        self.info = row["ZINFO"]

        self.user = row["ZUSER"]

        # Validate
        assert self.name is not None
        assert self.currency is not None
        assert self.opening_balance is not None
        assert self.info is not None
        assert self.user is not None


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
