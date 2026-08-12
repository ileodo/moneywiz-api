from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional

from moneywiz_api.model.raw_data_handler import RawDataHandler as RDH
from moneywiz_api.model.record import Record
from moneywiz_api.schema_profile import SchemaProfile
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

    def __init__(self, row, schema_profile: SchemaProfile | None = None):
        super().__init__(row)
        if schema_profile is not None and not schema_profile.is_known:
            raise ValueError("unsupported investment schema profile")
        self.account = row["ZINVESTMENTACCOUNT"]
        self.opening_number_of_shares = RDH.get_nullable_decimal(
            row, "ZOPENNINGNUMBEROFSHARES"
        )
        self.number_of_shares = RDH.get_profile_nullable_decimal(
            row,
            schema_profile.holding_number_of_shares_column if schema_profile else None,
            "ZNUMBEROFSHARES",
            "ZNUMBEROFSHARES1",
        )
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
        self.number_of_shares = self.number_of_shares or Decimal(0)

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
