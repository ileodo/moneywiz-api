from moneywiz_api import DEFAULT_SCHEMA_PROFILE
from decimal import Decimal

import pytest

from moneywiz_api.model.transaction import (
    DepositTransaction,
    RefundTransaction,
    TransferDepositTransaction,
    TransferWithdrawTransaction,
    WithdrawTransaction,
)


def transaction_row(**values):
    row = {
        "Z_ENT": 1,
        "ZOBJECTCREATIONDATE": None,
        "ZGID": "sanitized-example",
        "Z_PK": 1,
        "ZRECONCILED": 0,
        "ZAMOUNT1": 0.0,
        "ZDESC2": "Sanitized example",
        "ZDATE1": 0.0,
        "ZNOTES1": None,
    }
    row.update(values)
    return row


def test_transfer_deposit_derives_zero_legacy_original_amount():
    transaction = DEFAULT_SCHEMA_PROFILE.create_record(
        transaction_row(
            ZAMOUNT1=40.0,
            ZACCOUNT2=10,
            ZSENDERACCOUNT=11,
            ZSENDERTRANSACTION=2,
            ZORIGINALAMOUNT=0.0,
            ZORIGINALCURRENCY="USD",
            ZORIGINALSENDERAMOUNT=-40.0,
            ZORIGINALSENDERCURRENCY="USD",
            ZORIGINALFEE=0.0,
            ZORIGINALFEECURRENCY=None,
            ZORIGINALEXCHANGERATE=1.0,
        ),
        TransferDepositTransaction,
    )

    assert transaction.original_amount == Decimal("40.0")
    assert transaction.original_currency == "USD"
    assert transaction.sender_currency == "USD"


def test_transfer_withdraw_derives_zero_legacy_recipient_amount():
    transaction = DEFAULT_SCHEMA_PROFILE.create_record(
        transaction_row(
            ZAMOUNT1=-40.0,
            ZACCOUNT2=11,
            ZRECIPIENTACCOUNT1=10,
            ZRECIPIENTTRANSACTION=2,
            ZORIGINALAMOUNT=-40.0,
            ZORIGINALCURRENCY="USD",
            ZORIGINALRECIPIENTAMOUNT=0.0,
            ZORIGINALRECIPIENTCURRENCY="USD",
            ZORIGINALFEE=0.0,
            ZORIGINALFEECURRENCY=None,
            ZORIGINALEXCHANGERATE=1.0,
        ),
        TransferWithdrawTransaction,
    )

    assert transaction.recipient_amount == Decimal("40.0")
    assert transaction.original_currency == "USD"
    assert transaction.recipient_currency == "USD"


def test_withdraw_ignores_stale_rate_when_amounts_are_identical():
    transaction = DEFAULT_SCHEMA_PROFILE.create_record(
        transaction_row(
            ZAMOUNT1=-8.58,
            ZACCOUNT2=10,
            ZPAYEE2=None,
            ZORIGINALAMOUNT=-8.58,
            ZORIGINALCURRENCY="GBP",
            ZORIGINALEXCHANGERATE=1.1678321678321677,
            ZINVESTMENTSYMBOL=None,
        ),
        WithdrawTransaction,
    )

    assert transaction.original_exchange_rate is None


@pytest.mark.parametrize(
    "model_cls, amount",
    [
        (DepositTransaction, 10.0),
        (RefundTransaction, 10.0),
        (WithdrawTransaction, -10.0),
    ],
)
@pytest.mark.parametrize("investment_symbol", ["AAPL", None])
def test_transaction_loads_investment_symbol(model_cls, amount, investment_symbol):
    transaction = DEFAULT_SCHEMA_PROFILE.create_record(
        transaction_row(
            ZAMOUNT1=amount,
            ZACCOUNT2=10,
            ZPAYEE2=None,
            ZORIGINALAMOUNT=amount,
            ZORIGINALCURRENCY="USD",
            ZORIGINALEXCHANGERATE=1.0,
            ZINVESTMENTSYMBOL=investment_symbol,
        ),
        model_cls,
    )

    transaction.validate()
    assert transaction.investment_symbol == investment_symbol
    assert transaction.as_dict()["investment_symbol"] == investment_symbol
