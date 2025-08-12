from collections import defaultdict
from typing import Dict
from decimal import Decimal

import pytest
from moneywiz_api.model.transaction import (
    InvestmentBuyTransaction,
    InvestmentSellTransaction,
)
from moneywiz_api.types import ID

from conftest import (
    account_manager,
    transaction_manager,
    CASH_BALANCES,
    BALANCE_AS_OF_DATE,
    HOLDINGS_BALANCES,
)


@pytest.mark.parametrize(
    "test_account,expected_balance",
    CASH_BALANCES,
)
def test_cash_balance(test_account: int, expected_balance: Decimal):
    records = transaction_manager.get_all_for_account(
        test_account, until=BALANCE_AS_OF_DATE
    )
    balance = account_manager.get(test_account).opening_balance

    for record in records:
        balance += record.amount

    assert balance == pytest.approx(expected_balance, abs=0.01), f"balance={balance}"


@pytest.mark.parametrize(
    "test_account,expected_holding_balance",
    HOLDINGS_BALANCES,
)
def test_holding_balance(
    test_account: int, expected_holding_balance: Dict[ID, Decimal]
):
    records = transaction_manager.get_all_for_account(
        test_account, until=BALANCE_AS_OF_DATE
    )
    holding_balances: Dict[ID, Decimal] = defaultdict(lambda: Decimal(0))

    for record in records:
        if isinstance(record, InvestmentBuyTransaction):
            holding_balances[record.investment_holding] += record.number_of_shares
        if isinstance(record, InvestmentSellTransaction):
            holding_balances[record.investment_holding] -= record.number_of_shares

    assert holding_balances == pytest.approx(expected_holding_balance, abs=0.01), (
        holding_balances.items()
    )
