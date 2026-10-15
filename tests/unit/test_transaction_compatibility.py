from decimal import Decimal
from typing import cast

import pytest

from moneywiz_api import DEFAULT_SCHEMA_PROFILE
from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.managers.record_manager import RecordManager
from moneywiz_api.model.transaction import TransferWithdrawTransaction


def transfer_withdraw_row(**overrides):
    row = {
        "Z_ENT": 46,
        "ZOBJECTCREATIONDATE": 0.0,
        "ZGID": "transfer-withdraw",
        "Z_PK": 1,
        "ZRECONCILED": 0,
        "ZAMOUNT1": -10.0,
        "ZDESC2": "Transfer",
        "ZDATE1": 0.0,
        "ZNOTES1": None,
        "ZACCOUNT2": 10,
        "ZRECIPIENTACCOUNT1": 20,
        "ZRECIPIENTTRANSACTION": 2,
        "ZORIGINALAMOUNT": 0.0,
        "ZORIGINALCURRENCY": "EUR",
        "ZORIGINALRECIPIENTAMOUNT": 10.0,
        "ZORIGINALRECIPIENTCURRENCY": "USD",
        "ZORIGINALFEE": None,
        "ZORIGINALFEECURRENCY": None,
        "ZORIGINALEXCHANGERATE": 0.0,
    }
    row.update(overrides)
    return row


@pytest.mark.parametrize(
    ("original_amount", "recipient_amount"), [(0.0, 10.0), (-10.0, 10.0), (-10.0, 0.0)]
)
def test_transfer_withdraw_rejects_zero_rate(original_amount, recipient_amount) -> None:
    with pytest.raises(ValueError, match="zero exchange rate"):
        DEFAULT_SCHEMA_PROFILE.create_record(
            transfer_withdraw_row(
                ZORIGINALAMOUNT=original_amount,
                ZORIGINALRECIPIENTAMOUNT=recipient_amount,
            ),
            TransferWithdrawTransaction,
        )


@pytest.mark.parametrize("original_amount", [0.0, -10.0])
def test_transfer_withdraw_preserves_amount_with_nonzero_rate(original_amount) -> None:
    transaction = DEFAULT_SCHEMA_PROFILE.create_record(
        transfer_withdraw_row(
            ZORIGINALAMOUNT=original_amount, ZORIGINALEXCHANGERATE=1.0
        ),
        TransferWithdrawTransaction,
    )
    transaction.validate()

    assert transaction.original_amount == Decimal("-10.0")


def test_transfer_withdraw_preserves_stored_amount_with_rounded_rate() -> None:
    transaction = DEFAULT_SCHEMA_PROFILE.create_record(
        transfer_withdraw_row(
            ZAMOUNT1=-3.333,
            ZORIGINALRECIPIENTAMOUNT=10.0,
            ZORIGINALEXCHANGERATE=3.0,
        ),
        TransferWithdrawTransaction,
    )

    assert transaction.original_amount == Decimal("-3.333")


class TransferWithdrawManager(RecordManager):
    @property
    def ents(self):
        return {"TransferWithdrawTransaction": TransferWithdrawTransaction}


class TransferWithdrawAccessor:
    schema_profile = DEFAULT_SCHEMA_PROFILE

    def __init__(self, rows):
        self.rows = rows

    def query_objects(self, _typenames):
        return self.rows

    def typename_for(self, _ent_id):
        return "TransferWithdrawTransaction"


@pytest.mark.parametrize(
    ("original_amount", "recipient_amount"), [(0.0, 10.0), (-10.0, 10.0), (-10.0, 0.0)]
)
def test_transfer_manager_skips_zero_rate_and_loads_later_valid_row(
    original_amount, recipient_amount
) -> None:
    manager = TransferWithdrawManager()
    manager.load(
        cast(
            DatabaseAccessor,
            TransferWithdrawAccessor(
                [
                    transfer_withdraw_row(
                        ZORIGINALAMOUNT=original_amount,
                        ZORIGINALRECIPIENTAMOUNT=recipient_amount,
                    ),
                    transfer_withdraw_row(
                        Z_PK=2,
                        ZGID="valid-transfer-withdraw",
                        ZORIGINALEXCHANGERATE=1.0,
                    ),
                ]
            ),
        )
    )

    assert list(manager.records()) == [2]
    assert manager.load_errors == [(1, "TransferWithdrawTransaction", "ValueError")]
