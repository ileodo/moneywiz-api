import logging
from abc import ABC
from dataclasses import dataclass, field

from moneywiz_api.model.record import Record
from moneywiz_api.types import ID


logger = logging.getLogger(__name__)


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
        self._display_order = self.get_column_value("DISPLAYORDER")
        self._group_id = self.get_column_value("GROUPID")

        self.name = self.get_column_value("NAME")
        self.currency = self.get_column_value("CURRENCYNAME")
        self.opening_balance = self.get_column_value("OPENINGBALANCE")
        self.info = self.get_column_value("INFO")

        self.user = self.get_column_value("USER")

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

    statement_day: int = None  # day in the month

    def __init__(self, row):
        super().__init__(row)
        try:
            self.statement_day = row["ZSTATEMENTENDDAY"]

            # Validate
            assert self.statement_day is not None
        except KeyError:
            logger.debug("ZSTATEMENTENDDAY column not found. Is this MoneyWiz 3?")


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
