from dataclasses import dataclass

from moneywiz_api.model.record import Record
from moneywiz_api.model.schema_mapped_row import mapped_row, schema_field
from moneywiz_api.types import ID


@dataclass
class Tag(Record):
    FIELDS = {
        "name": schema_field("ZNAME6"),
        "user": schema_field("ZUSER8"),
    }

    name: str
    user: ID

    def __init__(self, row):
        row = mapped_row(row, self.__class__)
        super().__init__(row)
        self.name = row.get("name")
        self.user = row.get("user")

        # Fixes

    def validate(self) -> None:
        super().validate()
        assert self.name is not None, self.as_dict()
        assert self.user is not None, self.as_dict()
