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
        self.reconciled = self.get_column_value("RECONCILED") == 1
        self.amount = self.get_column_value("AMOUNT")
        self.description = self.get_column_value("DESC")
        self.date = self.get_column_value("DATE")
        self.notes = self.get_column_value("NOTES")

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
    original_exchange_rate: Optional[float]

    def __init__(self, row):
        super().__init__(row)
        self.account = self.get_column_value("ACCOUNT")
        self.amount = self.get_column_value("AMOUNT")
        self.payee = self.get_column_value("PAYEE")
        self.original_currency = self.get_column_value("ORIGINALCURRENCY")
        self.original_amount = self.get_column_value("ORIGINALAMOUNT")
        self.original_exchange_rate = self.get_column_value("ORIGINALEXCHANGERATE")

        # Validate
        self.validate()

    def validate(self):
        assert self.account is not None
        assert self.amount is not None
        # self.payee can be None
        assert self.original_currency is not None
        assert self.original_amount is not None

        assert self.amount * self.original_amount > 0  # Same sign
        if self.original_exchange_rate is not None:
            assert self.amount == pytest.approx(
                self.original_amount * self.original_exchange_rate, abs=0.001
            )


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
        self.account = self.get_column_value("ACCOUNT")
        self.amount = self.get_column_value("AMOUNT")

        self.fee = self.get_column_value("FEE")

        self.investment_holding = self.get_column_value("INVESTMENTHOLDING")
        self.number_of_shares = self.get_column_value("NUMBEROFSHARES")
        self.price_per_share = self.get_column_value("PRICEPERSHARE")

        # Fixes
        self.fee = max(self.fee, 0)

        # Validate
        self.validate()

    def validate(self):
        assert self.account is not None
        assert self.amount is not None
        assert self.amount <= 0
        assert self.fee is not None
        assert self.fee >= 0
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
        self.account = self.get_column_value("ACCOUNT")
        self.amount = self.get_column_value("AMOUNT")

        self.fee = self.get_column_value("FEE")

        self.investment_holding = self.get_column_value("INVESTMENTHOLDING")
        self.number_of_shares = self.get_column_value("NUMBEROFSHARES")
        self.price_per_share = self.get_column_value("PRICEPERSHARE")

        # Fixes
        self.fee = max(self.fee, 0)

        # Validate
        self.validate()

    def validate(self):
        assert self.account is not None
        assert self.amount is not None

        assert self.fee is not None
        assert self.fee >= 0
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
        self.account = self.get_column_value("ACCOUNT")
        self.amount = self.get_column_value("AMOUNT")
        self.reconcile_amount = self.get_column_value("RECONCILEAMOUNT")

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
        self.account = self.get_column_value("ACCOUNT")
        self.amount = self.get_column_value("AMOUNT")
        self.payee = self.get_column_value("PAYEE")

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

    original_amount: float  # ATTENTION: sign got fixed
    original_currency: str

    sender_amount: float
    sender_currency: str

    original_fee: Optional[float]
    original_fee_currency: Optional[str]

    original_exchange_rate: float

    def __init__(self, row):
        super().__init__(row)
        self.account = self.get_column_value("ACCOUNT")
        self.amount = self.get_column_value("AMOUNT")

        self.sender_account = self.get_column_value("SENDERACCOUNT")
        self.sender_transaction = self.get_column_value("SENDERTRANSACTION")

        self.original_amount = self.get_column_value("ORIGINALAMOUNT")
        self.original_currency = self.get_column_value("ORIGINALCURRENCY")
        self.sender_amount = self.get_column_value("ORIGINALSENDERAMOUNT")
        self.sender_currency = self.get_column_value("ORIGINALSENDERCURRENCY")

        self.original_fee = self.get_column_value("ORIGINALFEE")
        self.original_fee_currency = self.get_column_value("ORIGINALFEECURRENCY")

        self.original_exchange_rate = self.get_column_value("ORIGINALEXCHANGERATE")

        # Fixes
        self.original_amount = abs(self.original_amount)

        # Validate
        self.validate()

    def validate(self):
        assert self.account is not None
        assert self.amount is not None
        assert self.amount > 0
        assert self.sender_account is not None
        assert self.sender_transaction is not None
        assert self.original_amount is not None
        assert self.original_amount > 0
        assert self.original_currency is not None
        assert self.sender_amount is not None
        assert self.sender_amount <= 0
        assert self.sender_currency is not None

        if self.original_fee is not None and self.original_fee != 0:
            assert self.original_fee_currency is not None

        assert self.original_exchange_rate is not None

        # assert self.amount ==  self.original_amount # original_amount could be different with amount ZCURRENCYEXCHANGERATE is playing up
        if self.original_fee_currency == self.sender_currency:
            assert self.sender_amount == pytest.approx(
                -self.original_amount / self.original_exchange_rate, abs=0.001
            )

        else:
            assert self.original_amount == pytest.approx(
                -self.sender_amount * self.original_exchange_rate, abs=0.001
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

    original_amount: float  # always neg
    original_currency: str

    recipient_amount: float  # ATTENTION: sign got fixed
    recipient_currency: str

    original_fee: Optional[float]
    original_fee_currency: Optional[str]

    original_exchange_rate: float

    def __init__(self, row):
        super().__init__(row)
        self.account = self.get_column_value("ACCOUNT")
        self.amount = self.get_column_value("AMOUNT")

        self.recipient_account = self.get_column_value("RECIPIENTACCOUNT")
        self.recipient_transaction = self.get_column_value("RECIPIENTTRANSACTION")

        self.original_amount = self.get_column_value("ORIGINALAMOUNT")
        self.original_currency = self.get_column_value("ORIGINALCURRENCY")
        self.recipient_amount = self.get_column_value("ORIGINALRECIPIENTAMOUNT")
        self.recipient_currency = self.get_column_value("ORIGINALRECIPIENTCURRENCY")

        self.original_fee = self.get_column_value("ORIGINALFEE")
        self.original_fee_currency = self.get_column_value("ORIGINALFEECURRENCY")

        self.original_exchange_rate = self.get_column_value("ORIGINALEXCHANGERATE")

        # Fixes
        self.recipient_amount = abs(self.recipient_amount)

        # Validate
        self.validate()

    def validate(self):
        assert self.account is not None
        assert self.amount is not None
        assert self.amount < 0
        assert self.recipient_account is not None
        assert self.recipient_transaction is not None
        assert self.original_amount is not None
        assert self.original_amount < 0
        assert self.original_currency is not None
        assert self.recipient_amount is not None
        assert self.recipient_amount > 0
        assert self.recipient_currency is not None

        if self.original_fee is not None and self.original_fee != 0:
            assert self.original_fee_currency is not None

        assert self.original_exchange_rate is not None

        if self.original_fee_currency == self.recipient_currency:
            assert self.amount == self.original_amount

            assert self.amount == pytest.approx(
                -self.recipient_amount / self.original_exchange_rate, abs=0.001
            )

        else:
            assert self.original_amount == pytest.approx(
                self.amount + self.original_fee, abs=0.001
            )

            assert (self.amount + self.original_fee) == pytest.approx(
                -self.recipient_amount / self.original_exchange_rate, abs=0.001
            )


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
    original_amount: float  # neg: expense, pos: income ATTENTION: sign got fixed
    original_exchange_rate: Optional[float]

    def __init__(self, row):
        super().__init__(row)
        self.account = self.get_column_value("ACCOUNT")
        self.amount = self.get_column_value("AMOUNT")
        self.payee = self.get_column_value("PAYEE")

        self.original_currency = self.get_column_value("ORIGINALCURRENCY")
        self.original_amount = self.get_column_value("ORIGINALAMOUNT")
        self.original_exchange_rate = self.get_column_value("ORIGINALEXCHANGERATE")

        # Fixes
        if self.amount * self.original_amount < 0:
            self.original_amount = -self.original_amount

        # Validate
        self.validate()

    def validate(self):
        assert self.account is not None
        assert self.amount is not None
        # self.payee can be None
        assert self.original_currency is not None
        assert self.original_amount is not None

        assert self.amount * self.original_amount > 0

        if self.original_exchange_rate is not None:
            assert self.amount == pytest.approx(
                self.original_amount * self.original_exchange_rate, abs=0.001
            )
