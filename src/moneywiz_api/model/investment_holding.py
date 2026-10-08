from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from moneywiz_api.schema_profile import SchemaProfile

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional

from moneywiz_api.model.record import Record
from moneywiz_api.model.schema_fields import (
    schema_field as schema_field,
)
from moneywiz_api.types import ID


@dataclass
class InvestmentHolding(Record):
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

    def __init__(self, row, schema_profile: SchemaProfile):
        super().__init__(row, schema_profile)
        self._investment_object_type = self._schema_profile.get_field(
            row, self.__class__, "investment_object_type"
        )
        self._cost_basis_of_missing_ob_shares = self._schema_profile.get_field(
            row, self.__class__, "cost_basis_of_missing_ob_shares"
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
