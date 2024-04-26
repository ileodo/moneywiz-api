from typing import Dict, Callable, List
from decimal import Decimal

from moneywiz_api.model.investment_holding import InvestmentHolding
from moneywiz_api.managers.record_manager import RecordManager
from moneywiz_api.types import ID


class InvestmentHoldingManager(RecordManager[InvestmentHolding]):
    def __init__(self):
        super().__init__()

    @property
    def ents(self) -> Dict[str, Callable]:
        return {
            "InvestmentHolding": InvestmentHolding,
        }

    def get_holdings_for_account(self, account_id: ID) -> List[InvestmentHolding]:
        return [x for _, x in self.records().items() if x.account == account_id]

    def update_last_price(self, latest_price: Decimal):
        raise NotImplementedError()

    def update_price_table(self, latest_price: Decimal):
        raise NotImplementedError()
