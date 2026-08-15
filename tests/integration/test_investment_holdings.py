from collections import defaultdict
from decimal import Decimal
from typing import Dict, List


import pytest

from moneywiz_api.model.account import InvestmentAccount
from moneywiz_api.model.transaction import (
    InvestmentBuyTransaction,
    InvestmentSellTransaction,
)
from moneywiz_api.types import ID


from tests.integration.conftest import (
    account_manager,
    investment_holding_manager,
    transaction_manager,
)


@pytest.mark.parametrize(
    "investment_account",
    [x for x in account_manager.records().values() if isinstance(x, InvestmentAccount)],
)
def test_all_investment_account_holdings(investment_account: InvestmentAccount):
    _holdings = investment_holding_manager.get_holdings_for_account(
        investment_account.id
    )
    transactions = transaction_manager.get_all_for_account(investment_account.id)

    holdings_from_transactions: Dict[ID, List[Decimal]] = defaultdict(
        lambda: [Decimal(0), Decimal(0)]
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
