from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from moneywiz_api.schema.schema_profile import SchemaProfile

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict

from moneywiz_api.schema.raw_data_handler import RawDataHandler as RDH
from moneywiz_api.schema.schema_fields import schema_field as schema_field
from moneywiz_api.schema.schema_profile import SchemaProfile
from moneywiz_api.types import ENT_ID, ID


@dataclass
class Record:
    _raw: Dict[str, Any] = field(repr=False)
    ent: ENT_ID
    created_at: datetime
    gid: str = field(repr=False)
    id: ID

    def __init__(self, row, schema_profile: SchemaProfile):
        self._raw = row
        for field_name, value in schema_profile.get_fields(row, type(self)).items():
            setattr(self, field_name, value)

        # Fixes

    def validate(self) -> None:
        assert self._raw
        assert self.ent
        assert self.created_at is not None
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
        return original
