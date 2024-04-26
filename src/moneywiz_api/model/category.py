from dataclasses import dataclass
from typing import Optional

from moneywiz_api.model.record import Record
from moneywiz_api.types import CategoryType, ID


@dataclass
class Category(Record):
    """
    ENT: 19
    """

    name: str
    parent_id: Optional[int]
    type: CategoryType
    user: ID

    def __init__(self, row):
        super().__init__(row)
        self.name = row["ZNAME2"]
        self.parent_id = row["ZPARENTCATEGORY"]
        self.type = self._convert_type(row["ZTYPE2"])
        self.user = row["ZUSER3"]

        # Fixes

        # Validate
        assert self.name is not None, self.as_dict()
        assert self.type is not None, self.as_dict()
        assert self.user is not None, self.as_dict()

    @staticmethod
    def _convert_type(type_: Optional[int]) -> CategoryType:
        if type_ and type_ in [1, 2]:
            return "Expenses" if type_ == 1 else "Income"
        raise RuntimeError(f"Invalid type {type_}")
