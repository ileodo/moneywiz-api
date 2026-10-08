from __future__ import annotations

from dataclasses import dataclass

from moneywiz_api.model.record import Record
from moneywiz_api.types import ID


@dataclass
class Tag(Record):
    name: str
    user: ID

    def __init__(self, row, field_values):
        super().__init__(row, field_values)

        # Fixes

    def validate(self) -> None:
        super().validate()
        assert self.name is not None, self.as_dict()
        assert self.user is not None, self.as_dict()
