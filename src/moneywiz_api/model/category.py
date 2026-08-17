from dataclasses import dataclass
from typing import Optional

from moneywiz_api.model.record import Record
from moneywiz_api.model.schema_mapped_row import mapped_row, schema_field
from moneywiz_api.types import ID, CategoryType


@dataclass
class Category(Record):
    FIELDS = {
        "name": schema_field("ZNAME2"),
        "parent_id": schema_field("ZPARENTCATEGORY"),
        "type": schema_field("ZTYPE2"),
        "user": schema_field("ZUSER3"),
    }

    name: str
    parent_id: Optional[int]
    type: CategoryType
    user: ID

    def __init__(self, row):
        row = mapped_row(row, self.__class__)
        super().__init__(row)
        self.name = row.get("name")
        self.parent_id = row.get("parent_id")
        self.type = self._convert_type(row.get("type"))
        self.user = row.get("user")

        # Fixes

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
