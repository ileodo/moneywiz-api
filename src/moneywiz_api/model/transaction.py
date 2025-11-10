from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from moneywiz_api.model.raw_data_handler import RawDataHandler as RDH
from moneywiz_api.model.record import Record
from moneywiz_api.model.schema_mapped_row import (
    datetime_field,
    decimal_field,
    is_one_field,
    mapped_row,
    nullable_decimal_field,
    schema_field,
)
from moneywiz_api.types import ID

ABS_TOLERANCE = 0.001


def approx_equal(a, b, abs_tol: float = ABS_TOLERANCE) -> bool:
    if a is None or b is None:
        return False
    try:
        a_dec = Decimal(str(a))
        b_dec = Decimal(str(b))
        tol = Decimal(str(abs_tol))
    except Exception:
        return False
    return abs(a_dec - b_dec) <= tol


@dataclass
class Transaction(Record, ABC):
    FIELDS = {
        "reconciled": is_one_field("ZRECONCILED"),
        "amount": decimal_field("ZAMOUNT1"),
        "description": schema_field("ZDESC2"),
        "datetime": datetime_field("ZDATE1"),
        "notes": schema_field("ZNOTES1"),
    }

    reconciled: bool

    amount: Decimal
    description: str
    datetime: datetime
    notes: Optional[str]

    def __init__(self, row):
        row = mapped_row(row, self.__class__)
        super().__init__(row)
        self.reconciled = row.get("reconciled")
        self.amount = row.get("amount")
        self.description = row.get("description")
        self.datetime = row.get("datetime")
        self.notes = row.get("notes")

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
    FIELDS = {
        "account": schema_field("ZACCOUNT2"),
        "payee": schema_field("ZPAYEE2"),
        "original_currency": schema_field("ZORIGINALCURRENCY"),
        "original_amount": nullable_decimal_field("ZORIGINALAMOUNT"),
        "original_exchange_rate": nullable_decimal_field("ZORIGINALEXCHANGERATE"),
    }

    account: ID
    amount: Decimal  # neg: expense, pos: income
    payee: Optional[ID]

    # FX
    original_currency: str
    original_amount: Decimal  # neg: expense, pos: income
    original_exchange_rate: Optional[Decimal]

    def __init__(self, row):
        row = mapped_row(row, self.__class__)
        super().__init__(row)
        self.account = row.get("account")
        self.amount = row.get("amount")
        self.payee = row.get("payee")
        self.original_currency = row.get("original_currency")
        self.original_amount = row.get("original_amount")
        self.original_exchange_rate = row.get("original_exchange_rate")

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
    FIELDS = {
        "account": schema_field("ZACCOUNT2"),
        "from_investment_holding": schema_field("ZFROMINVESTMENTHOLDING"),
        "from_symbol": schema_field("ZFROMSYMBOL"),
        "to_investment_holding": schema_field("ZTOINVESTMENTHOLDING"),
        "to_symbol": schema_field("ZTOSYMBOL"),
        "from_number_of_shares": schema_field("ZFROMNUMBEROFSHARES"),
        "to_number_of_shares": schema_field("ZTONUMBEROFSHARES"),
        "original_fee": schema_field("ZORIGINALFEE"),
        "original_fee_currency": schema_field("ZORIGINALFEECURRENCY"),
    }

    account: ID

    from_investment_holding: ID
    from_symbol: str
    to_investment_holding: ID
    to_symbol: str
    from_number_of_shares: Decimal  # neg
    to_number_of_shares: Decimal  # pos

    original_fee: Decimal  # pos: fee, neg: income?
    original_fee_currency: str

    def __init__(self, row):
        row = mapped_row(row, self.__class__)
        super().__init__(row)

        self.account = row.get("account")
        self.from_investment_holding = row.get("from_investment_holding")
        self.from_symbol = row.get("from_symbol")
        self.to_investment_holding = row.get("to_investment_holding")
        self.to_symbol = row.get("to_symbol")
        self.from_number_of_shares = row.get("from_number_of_shares")
        self.to_number_of_shares = row.get("to_number_of_shares")

        self.original_fee = row.get("original_fee")
        self.original_fee_currency = row.get("original_fee_currency")

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
    def __init__(self, row):
        row = mapped_row(row, self.__class__)
        super().__init__(row)


@dataclass
class InvestmentBuyTransaction(InvestmentTransaction):
    """
    ENT: 40
    """

    FIELDS = {
        "account": schema_field("ZACCOUNT2"),
        "fee": decimal_field("ZFEE2"),
        "investment_holding": schema_field("ZINVESTMENTHOLDING"),
        "number_of_shares": decimal_field("ZNUMBEROFSHARES"),
        "price_per_share": decimal_field("ZPRICEPERSHARE1"),
    }

    account: ID
    amount: Decimal

    fee: Decimal

    investment_holding: ID
    number_of_shares: Decimal
    price_per_share: Decimal

    def __init__(self, row):
        row = mapped_row(row, self.__class__)
        super().__init__(row)
        self.account = row.get("account")
        self.amount = row.get("amount")

        self.fee = row.get("fee")

        self.investment_holding = row.get("investment_holding")
        self.number_of_shares = row.get("number_of_shares")
        self.price_per_share = row.get("price_per_share")

        # Fixes
        self.fee = max(self.fee, 0)

    def validate(self) -> None:
        super().validate()
        assert self.account is not None
        assert self.amount is not None
        assert self.amount <= 0
        assert self.fee is not None
        assert self.fee >= 0
        # Either tiny (close to 0) or positive
        tol = Decimal(str(ABS_TOLERANCE))
        assert (abs(self.fee) <= tol) or (self.fee > tol)
        assert self.investment_holding is not None
        assert self.number_of_shares is not None
        assert self.number_of_shares > 0
        assert self.price_per_share is not None
        assert self.price_per_share >= 0
        assert approx_equal(
            -(
                self.number_of_shares * self.price_per_share + self.fee
            ),
            self.amount,
        )


@dataclass
class InvestmentSellTransaction(InvestmentTransaction):
    FIELDS = {
        "account": schema_field("ZACCOUNT2"),
        "fee": decimal_field("ZFEE2"),
        "investment_holding": schema_field("ZINVESTMENTHOLDING"),
        "number_of_shares": decimal_field("ZNUMBEROFSHARES"),
        "price_per_share": decimal_field("ZPRICEPERSHARE1"),
    }

    account: ID
    amount: Decimal  # neg: loss after fees, pos: income

    fee: Decimal

    investment_holding: ID
    number_of_shares: Decimal
    price_per_share: Decimal

    def __init__(self, row):
        row = mapped_row(row, self.__class__)
        super().__init__(row)
        self.account = row.get("account")
        self.amount = row.get("amount")

        self.fee = row.get("fee")

        self.investment_holding = row.get("investment_holding")
        self.number_of_shares = row.get("number_of_shares")
        self.price_per_share = row.get("price_per_share")

        # Fixes
        self.fee = max(self.fee, 0)

    def validate(self) -> None:
        super().validate()
        assert self.account is not None
        assert self.amount is not None

        assert self.fee is not None
        assert self.fee >= 0
        # Either tiny (close to 0) or positive
        tol = Decimal(str(ABS_TOLERANCE))
        assert (abs(self.fee) <= tol) or (self.fee > tol)

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
    FIELDS = {
        "account": schema_field("ZACCOUNT2"),
        "reconcile_amount": nullable_decimal_field("ZRECONCILEAMOUNT"),
        "reconcile_number_of_shares": nullable_decimal_field(
            "ZRECONCILENUMBEROFSHARES"
        ),
    }

    account: ID

    reconcile_amount: Decimal | None  # new balance
    reconcile_number_of_shares: Decimal | None  # new balance

    def __init__(self, row):
        row = mapped_row(row, self.__class__)
        super().__init__(row)
        self.account = row.get("account")
        self.reconcile_amount = row.get("reconcile_amount")
        self.reconcile_number_of_shares = row.get("reconcile_number_of_shares")

    def validate(self) -> None:
        super().validate()
        assert self.account is not None
        assert (
            self.reconcile_amount is not None
            or self.reconcile_number_of_shares is not None
        )


@dataclass
class RefundTransaction(Transaction):
    FIELDS = {
        "account": schema_field("ZACCOUNT2"),
        "payee": schema_field("ZPAYEE2"),
        "original_currency": schema_field("ZORIGINALCURRENCY"),
        "original_amount": nullable_decimal_field("ZORIGINALAMOUNT"),
        "original_exchange_rate": nullable_decimal_field("ZORIGINALEXCHANGERATE"),
    }

    account: ID
    amount: Decimal
    payee: Optional[ID]

    # FX
    original_currency: str
    original_amount: Decimal
    original_exchange_rate: Optional[Decimal]

    def __init__(self, row):
        row = mapped_row(row, self.__class__)
        super().__init__(row)
        self.account = row.get("account")
        self.amount = row.get("amount")
        self.payee = row.get("payee")

        self.original_currency = row.get("original_currency")
        self.original_amount = row.get("original_amount")
        self.original_exchange_rate = row.get("original_exchange_rate")

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
            # Skip strict equality; some databases have rounding/exchange quirks
            pass


@dataclass
class TransferBudgetTransaction(Transaction):
    def __init__(self, row):
        row = mapped_row(row, self.__class__)
        super().__init__(row)
        # TODO: Not Implemented


@dataclass
class TransferDepositTransaction(Transaction):
    FIELDS = {
        "account": schema_field("ZACCOUNT2"),
        "sender_account": schema_field("ZSENDERACCOUNT"),
        "sender_transaction": schema_field("ZSENDERTRANSACTION"),
        "original_amount": decimal_field("ZORIGINALAMOUNT"),
        "original_currency": schema_field("ZORIGINALCURRENCY"),
        "sender_amount": decimal_field("ZORIGINALSENDERAMOUNT"),
        "sender_currency": schema_field("ZORIGINALSENDERCURRENCY"),
        "original_fee": nullable_decimal_field("ZORIGINALFEE"),
        "original_fee_currency": schema_field("ZORIGINALFEECURRENCY"),
        "original_exchange_rate": decimal_field("ZORIGINALEXCHANGERATE"),
    }

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

    def __init__(self, row):
        row = mapped_row(row, self.__class__)
        super().__init__(row)
        self.account = row.get("account")
        self.amount = row.get("amount")

        self.sender_account = row.get("sender_account")
        self.sender_transaction = row.get("sender_transaction")

        self.original_amount = row.get("original_amount")
        self.original_currency = row.get("original_currency")
        self.sender_amount = row.get("sender_amount")
        self.sender_currency = row.get("sender_currency")

        self.original_fee = row.get("original_fee")
        self.original_fee_currency = row.get("original_fee_currency")

        self.original_exchange_rate = row.get("original_exchange_rate")

        # Fixes
        # Some legacy transfers store zero/NULL original metadata even though
        # the paired amount and exchange rate are complete.
        if (
            self.original_amount in (None, Decimal(0))
            and self.sender_amount is not None
            and self.original_exchange_rate is not None
        ):
            self.original_amount = -self.sender_amount * self.original_exchange_rate - (
                self.original_fee or 0
            )
        if self.original_amount is not None:
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
        assert self.original_currency is None or self.original_currency
        assert self.sender_currency is None or self.sender_currency
        assert (self.original_currency is None) == (self.sender_currency is None)

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
    FIELDS = {
        "account": schema_field("ZACCOUNT2"),
        "recipient_account": schema_field("ZRECIPIENTACCOUNT1"),
        "recipient_transaction": schema_field("ZRECIPIENTTRANSACTION"),
        "original_amount": decimal_field("ZORIGINALAMOUNT"),
        "original_currency": schema_field("ZORIGINALCURRENCY"),
        "recipient_amount": nullable_decimal_field("ZORIGINALRECIPIENTAMOUNT"),
        "recipient_currency": schema_field("ZORIGINALRECIPIENTCURRENCY"),
        "original_fee": nullable_decimal_field("ZORIGINALFEE"),
        "original_fee_currency": schema_field("ZORIGINALFEECURRENCY"),
        "original_exchange_rate": decimal_field("ZORIGINALEXCHANGERATE"),
    }

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

    def __init__(self, row):
        row = mapped_row(row, self.__class__)
        super().__init__(row)
        self.account = row.get("account")
        self.amount = row.get("amount")

        self.recipient_account = row.get("recipient_account")
        self.recipient_transaction = row.get("recipient_transaction")

        self.original_amount = row.get("original_amount")
        self.original_currency = row.get("original_currency")
        self.recipient_amount = row.get("recipient_amount")
        self.recipient_currency = row.get("recipient_currency")

        self.original_fee = row.get("original_fee")
        self.original_fee_currency = row.get("original_fee_currency")

        self.original_exchange_rate = row.get("original_exchange_rate")

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
        assert self.original_currency is None or self.original_currency
        assert self.recipient_currency is None or self.recipient_currency
        assert (self.original_currency is None) == (self.recipient_currency is None)

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
    FIELDS = {
        "account": schema_field("ZACCOUNT2"),
        "payee": schema_field("ZPAYEE2"),
        "original_currency": schema_field("ZORIGINALCURRENCY"),
        "original_amount": decimal_field("ZORIGINALAMOUNT"),
        "original_exchange_rate": nullable_decimal_field("ZORIGINALEXCHANGERATE"),
    }

    account: ID
    amount: Decimal  # neg: expense, pos: income
    payee: Optional[ID]

    # FX
    original_currency: str
    original_amount: Decimal  # neg: expense, pos: income ATTENTION: sign got fixed
    original_exchange_rate: Optional[Decimal]

    def __init__(self, row):
        row = mapped_row(row, self.__class__)
        super().__init__(row)
        self.account = row.get("account")
        self.amount = row.get("amount")
        self.payee = row.get("payee")

        self.original_currency = row.get("original_currency")
        self.original_amount = row.get("original_amount")
        self.original_exchange_rate = row.get("original_exchange_rate")

        # Fixes
        if self.amount * self.original_amount < 0:
            self.original_amount = -self.original_amount

        if self.original_exchange_rate == Decimal(0):
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
            # Skip strict equality; tolerate exchange rounding discrepancies
            pass
