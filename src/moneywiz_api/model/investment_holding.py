from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from moneywiz_api.model.record import Record
from moneywiz_api.schema.schema_fields import (
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

    def __init__(self, row, field_values):
        super().__init__(row, field_values)

        # Fixes
        self.number_of_shares = self.number_of_shares or Decimal(0)

    def validate(self) -> None:
        super().validate()
        assert self.account is not None, self.as_dict()
        assert self.number_of_shares is not None, self.as_dict()

        assert self.symbol is not None, self.as_dict()
        assert self.description is not None, self.as_dict()
