from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping

from moneywiz_api.model.raw_data_handler import RawDataHandler as RDH

Converter = Callable[[Any], Any]


@dataclass(frozen=True)
class FieldSpec:
    aliases: tuple[str, ...]
    converter: Converter | None = None


class SchemaMappedRow:
    def __init__(self, raw_row: Dict[str, Any], model_cls: type):
        self.raw_row = raw_row
        self.fields = self._fields_for(model_cls)

    @classmethod
    def from_row(cls, row: Any, model_cls: type) -> "SchemaMappedRow":
        if isinstance(row, cls):
            return row
        return cls(row, model_cls)

    def get(self, field_name: str) -> Any:
        spec = self.fields[field_name]
        for alias in spec.aliases:
            if alias in self.raw_row:
                raw_value = self.raw_row[alias]
                if spec.converter is not None:
                    try:
                        converted_value = spec.converter(raw_value)
                        return converted_value
                    except Exception as e:
                        raise RuntimeError(
                            f"Failed to convert field {field_name} using column {alias} with value {raw_value}, "
                            f"the exception was: {e}. "
                            f"the row was: {RDH.filter_row(self.raw_row)}"
                        ) from e
                return raw_value

        raise KeyError(
            f"Could not resolve field {field_name}. "
            f"Tried {list(spec.aliases)}. "
            f"Available columns: {list(self.raw_row.keys())}"
        )

    def __getitem__(self, key: str) -> Any:
        return self.raw_row[key]

    def items(self):
        return self.raw_row.items()

    @staticmethod
    def _fields_for(model_cls: type) -> Dict[str, FieldSpec]:
        fields: Dict[str, FieldSpec] = {}
        for cls in reversed(model_cls.mro()):
            class_fields = getattr(cls, "FIELDS", {})
            fields.update(class_fields)
        return fields


# fields


def schema_field(*aliases: str, converter: Converter | None = None) -> FieldSpec:
    return FieldSpec(aliases=aliases, converter=converter)


def datetime_field(*aliases: str) -> FieldSpec:
    return schema_field(*aliases, converter=RDH.get_datetime)


def decimal_field(*aliases: str) -> FieldSpec:
    return schema_field(*aliases, converter=RDH.get_decimal)


def nullable_decimal_field(*aliases: str) -> FieldSpec:
    return schema_field(*aliases, converter=RDH.get_nullable_decimal)


def is_one_field(*aliases: str) -> FieldSpec:
    return schema_field(*aliases, converter=lambda raw_value: raw_value == 1)


def mapped_row(row: Any, model_cls: type) -> SchemaMappedRow:
    return SchemaMappedRow.from_row(row, model_cls)
