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
    parentId: Optional[int]
    type: CategoryType
    user: ID

    def __init__(self, row):
        super().__init__(row)
        self.name = row["ZNAME2"]
        self.parentId = row["ZPARENTCATEGORY"]
        self.type = self._convert_type(row["ZTYPE2"])
        self.user = row["ZUSER3"]

        # Validate
        assert self.name is not None
        assert self.type is not None
        assert self.user is not None

    @staticmethod
    def _convert_type(type_: Optional[int]) -> CategoryType:
        if not type_:
            raise Exception("Invalid type")
        if type_ not in [1, 2]:
            raise Exception("Invalid type")
        return "Expenses" if type_ == 1 else "Income"
