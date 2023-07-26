from abc import ABC
from dataclasses import dataclass
from typing import Optional

from moneywiz_api.model.record import Record
from moneywiz_api.types import ID

import pytest


@dataclass
class Transaction(Record, ABC):
    """
    ENT: 36
    """

    reconciled: bool

    amount: float
    description: str
    date: float
    notes: Optional[str]

    def __init__(self, row):
        super().__init__(row)
        self.reconciled = row["ZRECONCILED"] == 1
        self.amount = row["ZAMOUNT1"]
        self.description = row["ZDESC2"]
        self.date = row["ZDATE1"]
        self.notes = row["ZNOTES1"]

        # Validate
        assert self.reconciled is not None
        assert self.amount is not None
        assert self.description is not None
        assert self.date is not None
        # self.notes can be None


@dataclass
class DepositTransaction(Transaction):
    """
    ENT: 37
    """

    account: ID
    amount: float  # neg: expense, pos: income
    payee: Optional[ID]

    # FX
    original_currency: str
    original_amount: float  # neg: expense, pos: income
    original_exchange_rate: float

    def __init__(self, row):
        super().__init__(row)
        self.account = row["ZACCOUNT2"]
        self.amount = row["ZAMOUNT1"]
        self.payee = row["ZPAYEE2"]
        self.original_currency = row["ZORIGINALCURRENCY"]
        self.original_amount = row["ZORIGINALAMOUNT"]
        self.original_exchange_rate = row["ZORIGINALEXCHANGERATE"]

        # Validate
        self.validate()

    def validate(self):
        assert self.account is not None
        assert self.amount is not None
        # self.payee can be None
        assert self.original_currency is not None
        assert self.original_amount is not None
        assert self.original_exchange_rate is not None

        assert self.amount * self.original_amount > 0  # Same sign
        assert (
            self.amount == self.original_amount * self.original_exchange_rate
        )  # Same sign


@dataclass
class InvestmentExchangeTransaction(Transaction):
    """
    ENT: 38
    """

    def __init__(self, row):
        super().__init__(row)
        raise NotImplementedError()


@dataclass
class InvestmentTransaction(Transaction, ABC):
    """
    ENT: 39
    """

    def __init__(self, row):
        super().__init__(row)


@dataclass
class InvestmentBuyTransaction(InvestmentTransaction):
    """
    ENT: 40
    """

    account: ID
    amount: float

    fee: float

    investment_holding: ID
    number_of_shares: float
    price_per_share: float

    def __init__(self, row):
        super().__init__(row)
        self.account = row["ZACCOUNT2"]
        self.amount = row["ZAMOUNT1"]

        self.fee = row["ZFEE2"]

        self.investment_holding = row["ZINVESTMENTHOLDING"]
        self.number_of_shares = row["ZNUMBEROFSHARES1"]
        self.price_per_share = row["ZPRICEPERSHARE1"]

        # Validate
        self.validate()

    def validate(self):
        assert self.account is not None
        assert self.amount is not None
        assert self.amount <= 0
        assert self.fee is not None
        # assert self.fee >= 0 # Need DB Clean UP
        # Either tiny (close to 0) or positive
        assert abs(self.fee) == pytest.approx(0, abs=0.001) or self.fee > 0.001
        assert self.investment_holding is not None
        assert self.number_of_shares is not None
        assert self.number_of_shares > 0
        assert self.price_per_share is not None
        assert self.price_per_share >= 0
        assert -(
            self.number_of_shares * self.price_per_share + self.fee
        ) == pytest.approx(self.amount, abs=0.001)


@dataclass
class InvestmentSellTransaction(InvestmentTransaction):
    """
    ENT: 41
    """

    account: ID
    amount: float  # neg: loss after fees, pos: income

    fee: float

    investment_holding: ID
    number_of_shares: float
    price_per_share: float

    def __init__(self, row):
        super().__init__(row)
        self.account = row["ZACCOUNT2"]
        self.amount = row["ZAMOUNT1"]

        self.fee = row["ZFEE2"]

        self.investment_holding = row["ZINVESTMENTHOLDING"]
        self.number_of_shares = row["ZNUMBEROFSHARES1"]
        self.price_per_share = row["ZPRICEPERSHARE1"]

        # Validate
        self.validate()

    def validate(self):
        assert self.account is not None
        assert self.amount is not None

        assert self.fee is not None
        # assert self.fee >= 0 # Need DB Clean UP
        # Either tiny (close to 0) or positive
        assert abs(self.fee) == pytest.approx(0, abs=0.001) or self.fee > 0.001

        assert self.investment_holding is not None
        assert self.number_of_shares is not None
        assert self.number_of_shares > 0
        assert self.price_per_share is not None
        assert self.price_per_share >= 0
        assert (
            self.number_of_shares * self.price_per_share - self.fee
        ) == pytest.approx(self.amount, abs=0.001)


@dataclass
class ReconcileTransaction(Transaction):
    """
    ENT: 42
    """

    account: ID
    amount: float  # neg: expense, pos: income
    reconcile_amount: float  # new balance

    def __init__(self, row):
        super().__init__(row)
        self.account = row["ZACCOUNT2"]
        self.amount = row["ZAMOUNT1"]
        self.reconcile_amount = row["ZRECONCILEAMOUNT"]

        # Validate
        self.validate()

    def validate(self):
        assert self.account is not None
        assert self.amount is not None
        assert self.reconcile_amount is not None


@dataclass
class RefundTransaction(Transaction):
    """
    ENT: 43
    """

    account: ID
    amount: float
    payee: Optional[ID]

    def __init__(self, row):
        super().__init__(row)
        self.account = row["ZACCOUNT2"]
        self.amount = row["ZAMOUNT1"]
        self.payee = row["ZPAYEE2"]

        # Validate
        self.validate()

    def validate(self):
        assert self.account is not None
        assert self.amount is not None
        assert self.amount > 0


@dataclass
class TransferBudgetTransaction(Transaction):
    """
    ENT: 44
    """

    def __init__(self, row):
        super().__init__(row)
        # TODO: Not Implemented


@dataclass
class TransferDepositTransaction(Transaction):
    """
    ENT: 45
    """

    account: ID
    amount: float  # pos: in

    sender_account: ID
    sender_transaction: ID

    original_amount: float  # ATTENTION: should ignore sign
    original_currency: str

    sender_amount: float
    sender_currency: str

    original_exchange_rate: float

    def __init__(self, row):
        super().__init__(row)
        self.account = row["ZACCOUNT2"]
        self.amount = row["ZAMOUNT1"]

        self.sender_account = row["ZSENDERACCOUNT"]
        self.sender_transaction = row["ZSENDERTRANSACTION"]

        self.original_amount = row["ZORIGINALAMOUNT"]
        self.original_currency = row["ZORIGINALCURRENCY"]
        self.sender_amount = row["ZORIGINALSENDERAMOUNT"]
        self.sender_currency = row["ZORIGINALSENDERCURRENCY"]
        self.original_exchange_rate = row["ZORIGINALEXCHANGERATE"]

        # Validate
        self.validate()

    def validate(self):
        assert self.account is not None
        assert self.amount is not None
        assert self.amount > 0
        assert self.sender_account is not None
        assert self.sender_transaction is not None
        assert self.original_amount is not None
        assert self.original_currency is not None
        assert self.sender_amount is not None
        assert self.sender_amount <= 0
        assert self.sender_currency is not None

        assert self.original_exchange_rate is not None

        assert self.amount == abs(
            self.original_amount
        )  # sign of original_amount could be wrong, need DB cleanup
        assert self.amount == pytest.approx(
            -self.sender_amount * self.original_exchange_rate,
            abs=0.001,
        )


@dataclass
class TransferWithdrawTransaction(Transaction):
    """
    ENT: 46
    """

    account: ID
    amount: float  # neg: out

    recipient_account: ID
    recipient_transaction: ID

    original_amount: float  # ATTENTION: should ignore sign
    original_currency: str

    recipient_amount: float  # ATTENTION: sign could be wrong
    recipient_currency: str

    original_exchange_rate: float

    def __init__(self, row):
        super().__init__(row)
        self.account = row["ZACCOUNT2"]
        self.amount = row["ZAMOUNT1"]

        self.recipient_account = row["ZRECIPIENTACCOUNT1"]
        self.recipient_transaction = row["ZRECIPIENTTRANSACTION"]

        self.original_amount = row["ZORIGINALAMOUNT"]
        self.original_currency = row["ZORIGINALCURRENCY"]
        self.recipient_amount = row["ZORIGINALRECIPIENTAMOUNT"]
        self.recipient_currency = row["ZORIGINALRECIPIENTCURRENCY"]
        self.original_exchange_rate = row["ZORIGINALEXCHANGERATE"]

        # Validate
        self.validate()

    def validate(self):
        assert self.account is not None
        assert self.amount is not None
        assert self.amount < 0
        assert self.recipient_account is not None
        assert self.recipient_transaction is not None
        assert self.original_amount is not None
        assert self.original_currency is not None
        assert self.recipient_amount is not None
        # assert self.recipient_amount > 0  # Not Guaranteed
        assert self.recipient_currency is not None

        assert self.original_exchange_rate is not None

        assert self.amount == self.original_amount
        assert self.amount == pytest.approx(
            -abs(self.recipient_amount)  # recipient_amount sign could be wrong
            / self.original_exchange_rate,
            abs=0.001,
        ), self.filtered()


@dataclass
class WithdrawTransaction(Transaction):
    """
    ENT: 47
    """

    account: ID
    amount: float  # neg: expense, pos: income
    payee: Optional[ID]

    # FX
    original_currency: str
    original_amount: float  # neg: expense, pos: income
    original_exchange_rate: float

    def __init__(self, row):
        super().__init__(row)
        self.account = row["ZACCOUNT2"]
        self.amount = row["ZAMOUNT1"]
        self.payee = row["ZPAYEE2"]

        self.original_currency = row["ZORIGINALCURRENCY"]
        self.original_amount = row["ZORIGINALAMOUNT"]
        self.original_exchange_rate = row["ZORIGINALEXCHANGERATE"]

        # Validate
        self.validate()

    def validate(self):
        assert self.account is not None
        assert self.amount is not None
        # self.payee can be None
        assert self.original_currency is not None
        assert self.original_amount is not None
        assert self.original_exchange_rate is not None

        # assert self.amount * self.original_amount > 0  # Same sign not guaranteed
        assert abs(self.amount) == pytest.approx(
            abs(self.original_amount * self.original_exchange_rate), abs=0.001
        )  # Same sign
