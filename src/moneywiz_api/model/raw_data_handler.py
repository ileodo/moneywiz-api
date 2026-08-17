from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from moneywiz_api.utils import get_datetime


class RawDataHandler:
    @staticmethod
    def get_datetime(raw_value: Any) -> datetime:
        assert isinstance(raw_value, float) or isinstance(raw_value, int), (
            f"{raw_value} is not a float or int"
        )
        return get_datetime(raw_value)

    @staticmethod
    def get_nullable_decimal(raw_value: Any) -> Optional[Decimal]:
        if raw_value is None:
            return None
        else:
            return RawDataHandler.get_decimal(raw_value)

    @staticmethod
    def get_decimal(raw_value: Any) -> Decimal:
        assert isinstance(raw_value, float) or isinstance(raw_value, int), (
            f"{raw_value}, is not a float or int"
        )
        return Decimal(str(raw_value))

    @staticmethod
    def filter_row(row: Dict[str, Any]) -> Dict[str, Any]:
        copy = {k: v for k, v in row.items()}
        del copy["ZMANUALHISTORICALPRICESPERSHARE"]
        del copy["ZIMPORTLINKIDARRAY2"]
        del copy["ZIMPORTLINKIDARRAY"]
        del copy["ZBANKLOGOPRIMARYCOLOR"]
        return {
            k: v
            for k, v in copy.items()
            if (v is not None) and (not k.startswith("Z9_"))
        }
