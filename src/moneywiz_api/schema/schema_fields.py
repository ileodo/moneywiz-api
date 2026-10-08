from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from moneywiz_api.schema.raw_data_handler import RawDataHandler as RDH

Converter = Callable[[Any], Any]


@dataclass(frozen=True)
class FieldSpec:
    aliases: tuple[str, ...]
    converter: Converter | None = None


def schema_field(*aliases: str, converter: Converter | None = None) -> FieldSpec:
    return FieldSpec(aliases=aliases, converter=converter)


def datetime_field(*aliases: str, value_if_null: datetime | None = None) -> FieldSpec:
    def converter(raw_value: Any) -> datetime | None:
        if raw_value is None:
            return value_if_null
        return RDH.get_datetime(raw_value)

    return schema_field(*aliases, converter=converter)


def decimal_field(*aliases: str) -> FieldSpec:
    return schema_field(*aliases, converter=RDH.get_decimal)


def nullable_decimal_field(*aliases: str) -> FieldSpec:
    return schema_field(*aliases, converter=RDH.get_nullable_decimal)


def is_one_field(*aliases: str) -> FieldSpec:
    return schema_field(*aliases, converter=lambda raw_value: raw_value == 1)
