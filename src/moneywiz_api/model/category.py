from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from moneywiz_api.schema_profile import SchemaProfile


from dataclasses import dataclass
from typing import Optional, cast

from moneywiz_api.model.record import Record
from moneywiz_api.types import ID, CategoryType


@dataclass
class Category(Record):
    name: str
    parent_id: Optional[int]
    type: CategoryType
    user: ID

    def __init__(self, row, schema_profile: SchemaProfile):
        super().__init__(row, schema_profile)

        # Fixes
        self.type = self._convert_type(cast(Optional[int], self.type))

    def validate(self) -> None:
        super().validate()
        assert self.name is not None, self.as_dict()
        assert self.type is not None, self.as_dict()
        assert self.user is not None, self.as_dict()

    @staticmethod
    def _convert_type(type_: Optional[int]) -> CategoryType:
        if type_ and type_ in [1, 2]:
            return "Expenses" if type_ == 1 else "Income"
        raise RuntimeError(f"Invalid type {type_}")
