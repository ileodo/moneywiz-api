from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict

from moneywiz_api.model.raw_data_handler import RawDataHandler as RDH
from moneywiz_api.model.schema_mapped_row import datetime_field, mapped_row
from moneywiz_api.model.schema_mapped_row import schema_field as schema_field
from moneywiz_api.types import ENT_ID, ID


@dataclass
class Record:
    FIELDS = {
        "ent": schema_field("Z_ENT"),
        "created_at": datetime_field("ZOBJECTCREATIONDATE"),
        "gid": schema_field("ZGID"),
        "id": schema_field("Z_PK"),
    }

    _raw: Dict[str, Any] = field(repr=False)
    _ent: ENT_ID = field(repr=False)
    _created_at: datetime = field(repr=False)
    gid: str = field(repr=False)
    id: ID

    def __init__(self, row):
        row = mapped_row(row, self.__class__)
        self._raw = row.raw_row
        self._ent = row.get("ent")
        self._created_at = row.get("created_at")
        self.gid = row.get("gid")
        self.id = row.get("id")

        # Fixes

        # Validate

    def ent(self) -> ENT_ID:
        return self._ent

    def validate(self) -> None:
        assert self._raw
        assert self._ent
        assert self._created_at
        assert self.gid
        assert self.id

    def filtered(self) -> Dict[str, Any]:
        """
        Utility function to return cleaned up entities.
        it will exclude fields like binary, Z9_

        :return:
        """
        return RDH.filter_row(self._raw)

    def as_dict(self) -> Dict[str, Any]:
        """
        Utility function to return dataclass instance as a dict.

        :return:
        """
        original = asdict(self)
        del original["_raw"]
        del original["_ent"]
        del original["_created_at"]
        return original
