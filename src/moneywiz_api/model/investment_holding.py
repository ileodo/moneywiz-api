from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional

from moneywiz_api.model.record import Record
from moneywiz_api.model.schema_mapped_row import (
    decimal_field,
    is_one_field,
    mapped_row,
    nullable_decimal_field,
)
from moneywiz_api.model.schema_mapped_row import (
    schema_field as schema_field,
)
from moneywiz_api.types import ID


@dataclass
class InvestmentHolding(Record):
    FIELDS = {
        "account": schema_field("ZINVESTMENTACCOUNT"),
        "opening_number_of_shares": nullable_decimal_field("ZOPENNINGNUMBEROFSHARES"),
        "number_of_shares": nullable_decimal_field("ZNUMBEROFSHARES"),
        "symbol": schema_field("ZSYMBOL"),
        "holding_type": schema_field("ZHOLDINGTYPE"),
        "description": schema_field("ZDESC"),
        "price_per_share_available_online": is_one_field(
            "ZISPRICEPERSHAREAVAILABLEONLINE"
        ),
        "investment_object_type": schema_field("ZINVESTMENTOBJECTTYPE"),
        "cost_basis_of_missing_ob_shares": decimal_field("ZCOSTBASISOFMISSINGOBSHARES"),
    }

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
        row = mapped_row(row, self.__class__)
        super().__init__(row)
        self.account = row.get("account")
        self.opening_number_of_shares = row.get("opening_number_of_shares")
        self.number_of_shares = row.get("number_of_shares")
        self.symbol = row.get("symbol")
        self.holding_type = row.get("holding_type")
        self.description = row.get("description")
        self.price_per_share_available_online = row.get(
            "price_per_share_available_online"
        )

        self._investment_object_type = row.get("investment_object_type")
        self._cost_basis_of_missing_ob_shares = row.get(
            "cost_basis_of_missing_ob_shares"
        )

        # Fixes
        self.number_of_shares = self.number_of_shares or Decimal(0)

    def validate(self) -> None:
        super().validate()
        assert self.account is not None, self.as_dict()
        assert self.number_of_shares is not None, self.as_dict()

        assert self.symbol is not None, self.as_dict()
        assert self.description is not None, self.as_dict()

        assert self._investment_object_type is not None, self.as_dict()
        assert self._cost_basis_of_missing_ob_shares is not None, self.as_dict()

    def as_dict(self) -> Dict[str, Any]:
        original = super().as_dict()
        del original["_investment_object_type"]
        del original["_cost_basis_of_missing_ob_shares"]
        return original
