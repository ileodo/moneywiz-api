import logging
from dataclasses import dataclass

from moneywiz_api.model.record import Record
from moneywiz_api.types import ID


logger = logging.getLogger(__name__)


@dataclass
class Payee(Record):
    """
    ENT: 28
    """

    name: str
    user: ID

    def __init__(self, row):
        super().__init__(row)
        self.name = self.get_column_value("NAME")

        # Validate
        assert self.name is not None

        try:
            self.user = self.get_column_value("USER")

            # Validate
            assert self.user is not None
        except (KeyError, AssertionError):
            logger.debug("ZUSER7 column is NULL or was not found. Is this MoneyWiz 3?")
