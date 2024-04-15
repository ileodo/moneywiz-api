import re
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List

from moneywiz_api.types import ID, ENT_ID
from moneywiz_api.cache import MoneyWizApiCache


cache = MoneyWizApiCache()


@dataclass
class Record:
    _raw: Dict[str, Any] = field(repr=False)
    _ent: ENT_ID = field(repr=False)
    _created_at: float = field(repr=False)
    _non_null_columns: List[str] = field(repr=False)
    gid: str = field(repr=False)
    id: ID

    def __init__(self, row):
        self._raw = row
        self._ent = row["Z_ENT"]
        self._created_at = row["ZOBJECTCREATIONDATE"]
        self.gid = row["ZGID"]
        self.id = row["Z_PK"]
        self._non_null_columns = [k for k, v in self._raw.items() if v is not None]

        # Validate
        assert self._raw
        assert self._ent
        assert self._created_at
        assert self.gid
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
        del original["_non_null_columns"]
        return original

    def get_column_value(self, column_name_pattern: str) -> Any:

        cache_key_column = f"{self._ent}|{column_name_pattern}"
        if column := cache.get(cache_key_column):
            return self._raw[column]

        for _column in self._non_null_columns:
            if re.match(re.compile("".join(["^Z", column_name_pattern])), _column):
                cache[cache_key_column] = _column
                return self._raw[_column]
