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
    def get_decimal_alias(row: Dict[str, Any], *keys: str) -> Decimal:
        """Read a required decimal field from the first available column alias."""
        for key in keys:
            if key in row and row[key] is not None:
                return RawDataHandler.get_decimal(row[key])
        raise KeyError(f"none of the schema aliases are present: {', '.join(keys)}")

    @staticmethod
    def get_profile_decimal(
        row: Dict[str, Any], selected_key: Optional[str], *fallback_keys: str
    ) -> Decimal:
        """Read the schema-selected value, using aliases only for unknown profiles."""
        if selected_key is not None:
            return RawDataHandler.get_decimal(row[selected_key])
        return RawDataHandler.get_decimal_alias(row, *fallback_keys)

    @staticmethod
    def get_nullable_decimal_alias(
        row: Dict[str, Any], *keys: str
    ) -> Optional[Decimal]:
        """Read an optional decimal field from the first available column alias."""
        found_alias = False
        for key in keys:
            if key in row:
                found_alias = True
                if row[key] is not None:
                    return RawDataHandler.get_nullable_decimal(row[key])
        if found_alias:
            return None
        raise KeyError(f"none of the schema aliases are present: {', '.join(keys)}")

    @staticmethod
    def get_profile_nullable_decimal(
        row: Dict[str, Any], selected_key: Optional[str], *fallback_keys: str
    ) -> Optional[Decimal]:
        """Read an optional schema-selected value for a known profile."""
        if selected_key is not None:
            return RawDataHandler.get_nullable_decimal(row[selected_key])
        return RawDataHandler.get_nullable_decimal_alias(row, *fallback_keys)

    @staticmethod
    def filter_row(row: Dict[str, Any]) -> Dict[str, Any]:
        copy = {k: v for k, v in row.items()}
        for key in (
            "ZMANUALHISTORICALPRICESPERSHARE",
            "ZIMPORTLINKIDARRAY2",
            "ZIMPORTLINKIDARRAY",
            "ZBANKLOGOPRIMARYCOLOR",
        ):
            copy.pop(key, None)
        return {
            k: v
            for k, v in copy.items()
            if (v is not None) and (not k.startswith("Z9_"))
        }
