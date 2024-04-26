from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from decimal import Decimal

from moneywiz_api.model.raw_data_handler import RawDataHandler as RDH
from moneywiz_api.model.record import Record
from moneywiz_api.types import ID


@dataclass
class InvestmentHolding(Record):
    """
    ENT: 24
    """

    account: ID
    opening_number_of_shares: Optional[Decimal]

    number_of_shares: Decimal
    # price_per_share: Decimal
    symbol: str
    holding_type: Optional[str]
    description: str

    price_per_share_available_online: bool

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
    _cost_basis_of_missing_ob_shares: Decimal = field(repr=False)

    def __init__(self, row):
        super().__init__(row)
        self.account = row["ZINVESTMENTACCOUNT"]
        self.opening_number_of_shares = RDH.get_nullable_decimal(
            row, "ZOPENNINGNUMBEROFSHARES"
        )
        self.number_of_shares = RDH.get_decimal(row, "ZNUMBEROFSHARES")
        # self.price_per_share = row["ZPRICEPERSHARE"]
        self.symbol = row["ZSYMBOL"]
        self.holding_type = row["ZHOLDINGTYPE"]
        self.description = row["ZDESC"]
        self.price_per_share_available_online = (
            row["ZISPRICEPERSHAREAVAILABLEONLINE"] == 1
        )

        self._investment_object_type = row["ZINVESTMENTOBJECTTYPE"]
        self._cost_basis_of_missing_ob_shares = RDH.get_decimal(
            row, "ZCOSTBASISOFMISSINGOBSHARES"
        )

        # Fixes

        # Validate
        self.validate()

    def validate(self):
        assert self.account is not None, self.as_dict()
        assert self.number_of_shares is not None, self.as_dict()
        # assert self.price_per_share is not None
        assert self.symbol is not None, self.as_dict()
        assert self.description is not None, self.as_dict()

        assert self._investment_object_type is not None, self.as_dict()
        assert self._cost_basis_of_missing_ob_shares is not None, self.as_dict()

    def as_dict(self) -> Dict[str, Any]:
        original = super().as_dict()
        del original["_investment_object_type"]
        del original["_cost_basis_of_missing_ob_shares"]
        return original
