from abc import ABC
from dataclasses import dataclass, field
from decimal import Decimal

from moneywiz_api.model.record import Record
from moneywiz_api.model.schema_mapped_row import decimal_field, mapped_row, schema_field
from moneywiz_api.types import ID


@dataclass
class Account(Record, ABC):
    FIELDS = {
        "display_order": schema_field("ZDISPLAYORDER"),
        "group_id": schema_field("ZGROUPID"),
        "name": schema_field("ZNAME"),
        "currency": schema_field("ZCURRENCYNAME"),
        "opening_balance": decimal_field("ZOPENINGBALANCE"),
        "info": schema_field("ZINFO"),
        "user": schema_field("ZUSER"),
    }

    display_order: int = field(repr=False)
    group_id: int = field(repr=False)

    name: str
    currency: str
    opening_balance: Decimal  # might be a tiny number
    info: str
    user: ID

    def __init__(self, row):
        row = mapped_row(row, self.__class__)
        super().__init__(row)
        self.display_order = row.get("display_order")
        self.group_id = row.get("group_id")

        self.name = row.get("name")
        self.currency = row.get("currency")
        self.opening_balance = row.get("opening_balance")
        self.info = row.get("info")

        self.user = row.get("user")

        # Fixes

    def validate(self) -> None:
        super().validate()
        assert self.display_order is not None, self.as_dict()
        assert self.group_id is not None, self.as_dict()
        assert self.name is not None, self.as_dict()
        assert self.currency is not None, self.as_dict()
        assert self.opening_balance is not None, self.as_dict()
        assert self.info is not None, self.as_dict()
        assert self.user is not None, self.as_dict()


@dataclass
class BankChequeAccount(Account):
    def __init__(self, row):
        row = mapped_row(row, self.__class__)
        super().__init__(row)


@dataclass
class BankSavingAccount(Account):
    def __init__(self, row):
        super().__init__(row)


@dataclass
class CashAccount(Account):
    def __init__(self, row):
        super().__init__(row)


@dataclass
class CreditCardAccount(Account):
    FIELDS = {
        "statement_day": schema_field("ZSTATEMENTENDDAY"),
    }
    statement_day: int  # day in the month

    def __init__(self, row):
        super().__init__(row)
        self.statement_day = row.get("statement_day")

    def validate(self) -> None:
        super().validate()
        assert self.statement_day is not None


@dataclass
class LoanAccount(CreditCardAccount):
    def __init__(self, row):
        super().__init__(row)


@dataclass
class InvestmentAccount(Account):
    def __init__(self, row):
        super().__init__(row)


@dataclass
class ForexAccount(InvestmentAccount):
    def __init__(self, row):
        super().__init__(row)
