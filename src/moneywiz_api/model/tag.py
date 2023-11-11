from dataclasses import dataclass

from moneywiz_api.model.record import Record
from moneywiz_api.types import ID


@dataclass
class Tag(Record):
    """
    ENT: 35
    """

    name: str
    user: ID

    def __init__(self, row):
        super().__init__(row)
        self.name = row["ZNAME6"]
        self.user = row["ZUSER8"]

        # Validate
        assert self.name is not None
        assert self.user is not None
