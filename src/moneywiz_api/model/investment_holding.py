from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from moneywiz_api.model.record import Record
from moneywiz_api.types import ID


@dataclass
class InvestmentHolding(Record):
    """
    ENT: 24
    """

    account: ID
    opening_number_of_shares: Optional[float]

    number_of_shares: float
    # price_per_share: float
    symbol: str
    holding_type: Optional[str]
    description: str

    """
    Unsure about the usage.
    value can be 0,1
    
    seems like: 
        0 -> aggregate balance from all transactions
        1 -> use number_of_shares as balance
    """
    _investment_object_type: int = field(repr=False)

    """
    Unsure
    
    seems like the the cost for the shares which is not from transactions
    """
    _cost_basis_of_missing_ob_shares: float = field(repr=False)

    def __init__(self, row):
        super().__init__(row)
        self.account = row["ZINVESTMENTACCOUNT"]
        self.opening_number_of_shares = row["ZOPENNINGNUMBEROFSHARES"]
        self.number_of_shares = row["ZNUMBEROFSHARES"]
        # self.price_per_share = row["ZPRICEPERSHARE"]
        self.symbol = row["ZSYMBOL"]
        self.holding_type = row["ZHOLDINGTYPE"]
        self.description = row["ZDESC"]

        self._investment_object_type = row["ZINVESTMENTOBJECTTYPE"]
        self._cost_basis_of_missing_ob_shares = row["ZISFROMONLINEBANKING"]

        # Validate
        self.validate()

    def validate(self):
        assert self.account is not None
        assert self.number_of_shares is not None
        # assert self.price_per_share is not None
        assert self.symbol is not None
        assert self.description is not None

        assert self._investment_object_type is not None
        assert self._cost_basis_of_missing_ob_shares is not None

    def as_dict(self) -> Dict[str, Any]:
        original = super().as_dict()
        del original["_investment_object_type"]
        del original["_cost_basis_of_missing_ob_shares"]
        return original
