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

        self.parentId = self.get_column_value("PARENTCATEGORY")
        self.name = self.get_column_value("NAME")
        self.type = self._convert_type(self.get_column_value("TYPE"))
        self.user = self.get_column_value("USER")

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
