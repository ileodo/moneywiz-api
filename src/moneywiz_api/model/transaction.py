from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from moneywiz_api.schema.schema_profile import SchemaProfile

from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from moneywiz_api.model.record import Record
from moneywiz_api.types import ID

ABS_TOLERANCE = Decimal("0.001")


def approx_equal(a: Decimal, b: Decimal, abs_tol: Decimal = ABS_TOLERANCE) -> bool:
    return abs(a - b) <= abs_tol


@dataclass
class Transaction(Record, ABC):
    reconciled: bool

    amount: Decimal
    description: str
    datetime: datetime
    notes: Optional[str]

    def __init__(self, row, schema_profile: SchemaProfile):
        super().__init__(row, schema_profile)

        # Fixes

    def validate(self) -> None:
        super().validate()
        assert self.reconciled is not None, self.as_dict()
        assert self.amount is not None, self.as_dict()
        assert self.description is not None, self.as_dict()
        assert self.datetime is not None, self.as_dict()
        # self.notes can be None


@dataclass
class DepositTransaction(Transaction):
    account: ID
    amount: Decimal  # neg: expense, pos: income
    payee: Optional[ID]

    # FX
    original_currency: str
    original_amount: Decimal  # neg: expense, pos: income
    original_exchange_rate: Optional[Decimal]

    def __init__(self, row, schema_profile: SchemaProfile):
        super().__init__(row, schema_profile)

        # Fixes
        if self.original_exchange_rate == Decimal(0):
            self.original_exchange_rate = None

    def validate(self) -> None:
        super().validate()
        assert self.account is not None, self.as_dict()
        assert self.amount is not None, self.as_dict()
        # self.payee can be None
        assert self.original_currency is not None, self.as_dict()
        assert self.original_amount is not None, self.as_dict()

        assert self.amount * self.original_amount > 0, self.as_dict()  # Same sign
        if self.original_exchange_rate is not None:
            assert approx_equal(
                self.amount, self.original_amount * self.original_exchange_rate
            ), self.as_dict()


@dataclass
class InvestmentExchangeTransaction(Transaction):
    account: ID

    from_investment_holding: ID
    from_symbol: str
    to_investment_holding: ID
    to_symbol: str
    from_number_of_shares: Decimal  # neg
    to_number_of_shares: Decimal  # pos

    original_fee: Decimal  # pos: fee, neg: income?
    original_fee_currency: str

    def __init__(self, row, schema_profile: SchemaProfile):
        super().__init__(row, schema_profile)

        # Fixes
        if self.original_fee_currency == self.from_symbol:
            self.from_number_of_shares += self.original_fee
        elif self.original_fee_currency == self.to_symbol:
            self.to_number_of_shares += self.original_fee

    def validate(self) -> None:
        super().validate()
        assert self.from_investment_holding is not None
        assert self.from_symbol
        assert self.to_investment_holding is not None
        assert self.to_symbol
        assert self.from_number_of_shares <= 0
        assert self.to_number_of_shares >= 0
        assert self.original_fee is not None
        assert self.original_fee_currency in [self.from_symbol, self.to_symbol]


@dataclass
class InvestmentTransaction(Transaction, ABC):
    def __init__(self, row, schema_profile: SchemaProfile):
        super().__init__(row, schema_profile)


@dataclass
class InvestmentBuyTransaction(InvestmentTransaction):
    """
    ENT: 40
    """

    account: ID
    amount: Decimal

    fee: Decimal

    investment_holding: ID
    number_of_shares: Decimal
    price_per_share: Decimal

    def __init__(self, row, schema_profile: SchemaProfile):
        super().__init__(row, schema_profile)

        # Fixes
        self.fee = max(self.fee, Decimal(0))

    def validate(self) -> None:
        super().validate()
        assert self.account is not None
        assert self.amount is not None
        assert self.amount <= 0
        assert self.fee is not None
        assert self.fee >= 0
        # Either tiny (close to 0) or positive
        assert (abs(self.fee) <= ABS_TOLERANCE) or (self.fee > ABS_TOLERANCE)
        assert self.investment_holding is not None
        assert self.number_of_shares is not None
        assert self.number_of_shares > 0
        assert self.price_per_share is not None
        assert self.price_per_share >= 0
        assert approx_equal(
            -(self.number_of_shares * self.price_per_share + self.fee),
            self.amount,
        )


@dataclass
class InvestmentSellTransaction(InvestmentTransaction):
    account: ID
    amount: Decimal  # neg: loss after fees, pos: income

    fee: Decimal

    investment_holding: ID
    number_of_shares: Decimal
    price_per_share: Decimal

    def __init__(self, row, schema_profile: SchemaProfile):
        super().__init__(row, schema_profile)

        # Fixes
        self.fee = max(self.fee, Decimal(0))

    def validate(self) -> None:
        super().validate()
        assert self.account is not None
        assert self.amount is not None

        assert self.fee is not None
        assert self.fee >= 0
        # Either tiny (close to 0) or positive
        assert (abs(self.fee) <= ABS_TOLERANCE) or (self.fee > ABS_TOLERANCE)

        assert self.investment_holding is not None
        assert self.number_of_shares is not None
        assert self.number_of_shares > 0
        assert self.price_per_share is not None
        assert self.price_per_share >= 0
        assert approx_equal(
            self.number_of_shares * self.price_per_share - self.fee, self.amount
        )


@dataclass
class ReconcileTransaction(Transaction):
    account: ID

    reconcile_amount: Decimal | None  # new balance
    reconcile_number_of_shares: Decimal | None  # new balance

    def __init__(self, row, schema_profile: SchemaProfile):
        super().__init__(row, schema_profile)

    def validate(self) -> None:
        super().validate()
        assert self.account is not None
        assert (
            self.reconcile_amount is not None
            or self.reconcile_number_of_shares is not None
        )


@dataclass
class RefundTransaction(Transaction):
    account: ID
    amount: Decimal
    payee: Optional[ID]

    # FX
    original_currency: str
    original_amount: Decimal
    original_exchange_rate: Optional[Decimal]

    def __init__(self, row, schema_profile: SchemaProfile):
        super().__init__(row, schema_profile)

        # Fixes
        if self.original_exchange_rate == Decimal(0):
            self.original_exchange_rate = None

    def validate(self) -> None:
        super().validate()
        assert self.account is not None
        assert self.amount is not None
        assert self.amount > 0

        assert self.original_currency is not None
        assert self.original_amount is not None
        assert self.original_amount > 0

        if self.original_exchange_rate is not None:
            assert approx_equal(
                self.amount, self.original_amount * self.original_exchange_rate
            )


@dataclass
class TransferBudgetTransaction(Transaction):
    def __init__(self, row, schema_profile: SchemaProfile):
        super().__init__(row, schema_profile)
        # TODO: Not Implemented


@dataclass
class TransferDepositTransaction(Transaction):
    account: ID
    amount: Decimal  # pos: in

    sender_account: ID
    sender_transaction: ID

    original_amount: Decimal  # ATTENTION: sign got fixed
    original_currency: str

    sender_amount: Decimal
    sender_currency: str

    original_fee: Optional[Decimal]
    original_fee_currency: Optional[str]

    original_exchange_rate: Decimal

    def __init__(self, row, schema_profile: SchemaProfile):
        super().__init__(row, schema_profile)

        # Fixes
        # Some legacy transfers store zero original metadata even though
        # the paired amount and exchange rate are complete.
        if (
            self.original_amount == Decimal(0)
            and self.sender_amount is not None
            and self.original_exchange_rate is not None
        ):
            self.original_amount = -self.sender_amount * self.original_exchange_rate - (
                self.original_fee or 0
            )
        self.original_amount = abs(self.original_amount)

    def validate(self) -> None:
        super().validate()
        assert self.account is not None
        assert self.amount is not None
        assert self.amount > 0
        assert self.sender_account is not None
        assert self.sender_transaction is not None
        assert self.original_amount is not None
        assert self.original_amount > 0
        assert self.sender_amount is not None
        assert self.sender_amount <= 0
        assert self.original_currency is not None
        assert self.sender_currency is not None

        if self.original_fee is not None and self.original_fee != 0:
            assert self.original_fee_currency is not None

        assert self.original_exchange_rate is not None

        # assert self.amount ==  self.original_amount # original_amount could be different with amount ZCURRENCYEXCHANGERATE is playing up
        assert approx_equal(
            self.original_amount,
            -self.sender_amount * self.original_exchange_rate
            - (self.original_fee or 0),
        )


@dataclass
class TransferWithdrawTransaction(Transaction):
    account: ID
    amount: Decimal  # neg: out

    recipient_account: ID
    recipient_transaction: ID

    original_amount: Decimal  # always neg
    original_currency: str

    recipient_amount: Decimal  # ATTENTION: sign got fixed
    recipient_currency: str

    original_fee: Optional[Decimal]
    original_fee_currency: Optional[str]

    original_exchange_rate: Decimal

    def __init__(self, row, schema_profile: SchemaProfile):
        super().__init__(row, schema_profile)

        # Fixes
        if (
            self.recipient_amount in (None, Decimal(0))
            and self.original_amount is not None
            and self.original_exchange_rate is not None
        ):
            self.recipient_amount = -self.original_amount * self.original_exchange_rate
        if self.recipient_amount is not None:
            self.recipient_amount = abs(self.recipient_amount)

    def validate(self) -> None:
        super().validate()
        assert self.account is not None
        assert self.amount is not None
        assert self.amount < 0
        assert self.recipient_account is not None
        assert self.recipient_transaction is not None
        assert self.original_amount is not None
        assert self.original_amount < 0
        assert self.recipient_amount is not None
        assert self.recipient_amount > 0
        assert self.original_currency is not None
        assert self.recipient_currency is not None

        if self.original_fee is not None and self.original_fee != 0:
            assert self.original_fee_currency is not None

        assert self.original_exchange_rate is not None

        assert self.amount == self.original_amount
        assert approx_equal(
            self.amount,
            -self.recipient_amount / self.original_exchange_rate,
        )


@dataclass
class WithdrawTransaction(Transaction):
    account: ID
    amount: Decimal  # neg: expense, pos: income
    payee: Optional[ID]

    # FX
    original_currency: str
    original_amount: Decimal  # neg: expense, pos: income ATTENTION: sign got fixed
    original_exchange_rate: Optional[Decimal]

    def __init__(self, row, schema_profile: SchemaProfile):
        super().__init__(row, schema_profile)

        # Fixes
        if self.amount * self.original_amount < 0:
            self.original_amount = -self.original_amount

        if self.original_exchange_rate == Decimal(0):
            self.original_exchange_rate = None
        elif (
            self.original_exchange_rate != Decimal(1)
            and self.amount == self.original_amount
        ):
            # The rate is stale when no currency conversion took place.
            self.original_exchange_rate = None

    def validate(self) -> None:
        super().validate()
        assert self.account is not None
        assert self.amount is not None
        # self.payee can be None
        assert self.original_currency is not None
        assert self.original_amount is not None

        assert self.amount * self.original_amount > 0

        if self.original_exchange_rate is not None:
            assert approx_equal(
                self.amount, self.original_amount * self.original_exchange_rate
            )
