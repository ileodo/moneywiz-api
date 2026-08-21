from decimal import Decimal

from moneywiz_api.model.transaction import (
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
    transaction = TransferDepositTransaction(
        transaction_row(
            ZAMOUNT1=40.0,
            ZACCOUNT2=10,
            ZSENDERACCOUNT=11,
            ZSENDERTRANSACTION=2,
            ZORIGINALAMOUNT=0.0,
            ZORIGINALCURRENCY=None,
            ZORIGINALSENDERAMOUNT=-40.0,
            ZORIGINALSENDERCURRENCY=None,
            ZORIGINALFEE=0.0,
            ZORIGINALFEECURRENCY=None,
            ZORIGINALEXCHANGERATE=1.0,
        )
    )

    assert transaction.original_amount == Decimal("40.0")
    assert transaction.original_currency is None
    assert transaction.sender_currency is None


def test_transfer_withdraw_derives_zero_legacy_recipient_amount():
    transaction = TransferWithdrawTransaction(
        transaction_row(
            ZAMOUNT1=-40.0,
            ZACCOUNT2=11,
            ZRECIPIENTACCOUNT1=10,
            ZRECIPIENTTRANSACTION=2,
            ZORIGINALAMOUNT=-40.0,
            ZORIGINALCURRENCY=None,
            ZORIGINALRECIPIENTAMOUNT=0.0,
            ZORIGINALRECIPIENTCURRENCY=None,
            ZORIGINALFEE=0.0,
            ZORIGINALFEECURRENCY=None,
            ZORIGINALEXCHANGERATE=1.0,
        )
    )

    assert transaction.recipient_amount == Decimal("40.0")
    assert transaction.original_currency is None
    assert transaction.recipient_currency is None


def test_withdraw_ignores_stale_rate_when_amounts_are_identical():
    transaction = WithdrawTransaction(
        transaction_row(
            ZAMOUNT1=-8.58,
            ZACCOUNT2=10,
            ZPAYEE2=None,
            ZORIGINALAMOUNT=-8.58,
            ZORIGINALCURRENCY="GBP",
            ZORIGINALEXCHANGERATE=1.1678321678321677,
        )
    )

    assert transaction.original_exchange_rate is None
