from pathlib import Path

from moneywiz_api import MoneywizApi
from tests.integration.test_config import (
    BALANCE_AS_OF_DATE,
    CASH_BALANCES,
    HOLDINGS_BALANCES,
    TEST_DB_PATH,
)

moneywizApi = MoneywizApi(Path(TEST_DB_PATH))

accessor = moneywizApi.accessor
account_manager = moneywizApi.account_manager
payee_manager = moneywizApi.payee_manager
category_manager = moneywizApi.category_manager
transaction_manager = moneywizApi.transaction_manager
investment_holding_manager = moneywizApi.investment_holding_manager
