from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from moneywiz_api.schema.schema_profile import SchemaProfile

from dataclasses import dataclass

from moneywiz_api.model.record import Record
from moneywiz_api.types import ID


@dataclass
class Tag(Record):
    name: str
    user: ID

    def __init__(self, row, schema_profile: SchemaProfile):
        super().__init__(row, schema_profile)

        # Fixes

    def validate(self) -> None:
        super().validate()
        assert self.name is not None, self.as_dict()
        assert self.user is not None, self.as_dict()
