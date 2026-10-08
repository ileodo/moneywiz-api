from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import Optional
from decimal import Decimal

from moneywiz_api.model.record import Record
from moneywiz_api.types import ID


@dataclass
class Account(Record, ABC):
    display_order: int = field(repr=False)
    group_id: int = field(repr=False)

    name: str
    currency: str
    opening_balance: Decimal  # might be a tiny number
    info: Optional[str]
    user: ID

    def __init__(self, row, field_values):
        super().__init__(row, field_values)

        # Fixes

    def validate(self) -> None:
        super().validate()
        assert self.display_order is not None, self.as_dict()
        assert self.group_id is not None, self.as_dict()
        assert self.name is not None, self.as_dict()
        assert self.currency is not None, self.as_dict()
        assert self.opening_balance is not None, self.as_dict()
        # self.info can be None in some databases
        assert self.user is not None, self.as_dict()


@dataclass
class BankChequeAccount(Account):
    def __init__(self, row, field_values):
        super().__init__(row, field_values)


@dataclass
class BankSavingAccount(Account):
    def __init__(self, row, field_values):
        super().__init__(row, field_values)


@dataclass
class CashAccount(Account):
    def __init__(self, row, field_values):
        super().__init__(row, field_values)


@dataclass
class CreditCardAccount(Account):
    statement_day: int  # day in the month

    def __init__(self, row, field_values):
        super().__init__(row, field_values)

    def validate(self) -> None:
        super().validate()
        assert self.statement_day is not None


@dataclass
class LoanAccount(CreditCardAccount):
    def __init__(self, row, field_values):
        super().__init__(row, field_values)


@dataclass
class InvestmentAccount(Account):
    def __init__(self, row, field_values):
        super().__init__(row, field_values)


@dataclass
class ForexAccount(InvestmentAccount):
    def __init__(self, row, field_values):
        super().__init__(row, field_values)
