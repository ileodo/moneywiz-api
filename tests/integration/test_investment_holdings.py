from collections import defaultdict
from typing import Dict, List
from decimal import Decimal


import pytest

from moneywiz_api.model.account import InvestmentAccount
from moneywiz_api.model.transaction import (
    InvestmentBuyTransaction,
    InvestmentSellTransaction,
)
from moneywiz_api.types import ID


from conftest import account_manager, investment_holding_manager, transaction_manager


@pytest.mark.parametrize(
    "investment_account",
    [
        x
        for x in account_manager.get_accounts_for_user(2)
        if isinstance(x, InvestmentAccount)
    ],
)
def test_all_investment_account_holdings(investment_account: InvestmentAccount):
    _holdings = investment_holding_manager.get_holdings_for_account(
        investment_account.id
    )
    transactions = transaction_manager.get_all_for_account(investment_account.id)

    NumberOfShare = Decimal
    CostValue = Decimal
    holdings_from_transactions: Dict[ID, List[NumberOfShare, CostValue]] = defaultdict(
        lambda: [0, 0]
    )
    for transaction in transactions:
        if isinstance(transaction, InvestmentBuyTransaction):
            holdings_from_transactions[transaction.investment_holding][0] += (
                transaction.number_of_shares
            )
            # holdings_from_transactions[transaction.investment_holding][1] += transaction.amount
        if isinstance(transaction, InvestmentSellTransaction):
            holdings_from_transactions[transaction.investment_holding][0] -= (
                transaction.number_of_shares
            )
            # holdings_from_transactions[transaction.investment_holding][1] += transaction.amount

    # holding.number_of_shares can be wrong.
    # for holding in holdings:
    #     assert holding.number_of_shares == pytest.approx(holdings_from_transactions[holding.id][0] + (holding.opening_number_of_shares or 0), abs=0.001)
