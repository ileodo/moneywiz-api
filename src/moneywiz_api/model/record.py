from dataclasses import dataclass, asdict, field
from typing import Dict, Any

from moneywiz_api.types import ID, ENT_ID


@dataclass
class Record:
    _raw: Dict[str, Any] = field(repr=False)
    _ent: ENT_ID = field(repr=False)
    _created_at: float = field(repr=False)
    _gid: str = field(repr=False)
    id: ID

    def __init__(self, row):
        self._raw = row
        self._ent = row["Z_ENT"]
        self._created_at = row["ZOBJECTCREATIONDATE"]
        self._gid = row["ZGID"]
        self.id = row["Z_PK"]

        # Validate
        assert self._raw
        assert self._ent
        assert self._created_at
        assert self._gid
        assert self.id

    def ent(self) -> ENT_ID:
        return self._ent

    def validate(self):
        pass

    def fix(self):
        pass

    def filtered(self) -> Dict[str, Any]:
        """
        Utility function to return cleaned up entities.
        it will exclude fields like binary, Z9_

        :return:
        """
        copy = {k: v for k, v in self._raw.items()}
        # del copy["ZGID"]
        del copy["ZMANUALHISTORICALPRICESPERSHARE"]
        del copy["ZIMPORTLINKIDARRAY2"]
        del copy["ZIMPORTLINKIDARRAY"]
        del copy["ZBANKLOGOPRIMARYCOLOR"]
        return {
            k: v
            for k, v in copy.items()
            if (v is not None) and (not k.startswith("Z9_"))
        }

    def as_dict(self) -> Dict[str, Any]:
        """
        Utility function to return dataclass instance as a dict.

        :return:
        """
        original = asdict(self)
        del original["_raw"]
        del original["_ent"]
        del original["_created_at"]
        del original["_gid"]
        return original
