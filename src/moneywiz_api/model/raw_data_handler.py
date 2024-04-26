from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from moneywiz_api.utils import get_datetime


class RawDataHandler:

    @staticmethod
    def get_datetime(row: Dict[str, Any], key: str) -> datetime:
        raw_value = row[key]
        assert isinstance(raw_value, float) or isinstance(
            raw_value, int
        ), f"row['{key}'] = {row[key]}, is not a float or int, where row is: " + str(
            RawDataHandler.filter_row(row)
        )
        return get_datetime(raw_value)

    @staticmethod
    def get_nullable_decimal(row: Dict[str, Any], key: str) -> Optional[Decimal]:
        raw_value = row[key]
        if raw_value is None:
            return None
        else:
            return RawDataHandler.get_decimal(row, key)

    @staticmethod
    def get_decimal(row: Dict[str, Any], key: str) -> Decimal:
        raw_value = row[key]
        assert isinstance(raw_value, float) or isinstance(
            raw_value, int
        ), f"row['{key}'] = {row[key]}, is not a float or int, where row is: " + str(
            RawDataHandler.filter_row(row)
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
