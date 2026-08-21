import os
from pathlib import Path
from typing import Any

import pytest

from tests.integration import test_config

BALANCE_AS_OF_DATE = test_config.BALANCE_AS_OF_DATE
CASH_BALANCES = test_config.CASH_BALANCES
HOLDINGS_BALANCES = test_config.HOLDINGS_BALANCES


class _UnconfiguredManager:
    def records(self):
        return {}


if os.environ.get("MONEYWIZ_TEST_DB_PATH"):
    from moneywiz_api import MoneywizApi

    TEST_DB_PATH = test_config.get_test_db_path()
    moneywizApi = MoneywizApi(TEST_DB_PATH)

    accessor: Any = moneywizApi.accessor
    account_manager: Any = moneywizApi.account_manager
    payee_manager: Any = moneywizApi.payee_manager
    category_manager: Any = moneywizApi.category_manager
    transaction_manager: Any = moneywizApi.transaction_manager
    investment_holding_manager: Any = moneywizApi.investment_holding_manager
else:
    accessor = _UnconfiguredManager()
    account_manager = _UnconfiguredManager()
    payee_manager = _UnconfiguredManager()
    category_manager = _UnconfiguredManager()
    transaction_manager = _UnconfiguredManager()
    investment_holding_manager = _UnconfiguredManager()


def pytest_collection_modifyitems(config, items):
    """Skip integration tests only after their initial conftest can load safely."""
    if os.environ.get("MONEYWIZ_TEST_DB_PATH"):
        return
    integration_directory = Path(__file__).parent.resolve()
    skip = pytest.mark.skip(reason="integration tests require MONEYWIZ_TEST_DB_PATH")
    for item in items:
        if integration_directory in Path(str(item.path)).resolve().parents:
            item.add_marker(skip)
