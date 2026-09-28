from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict

from moneywiz_api.model.raw_data_handler import RawDataHandler as RDH
from moneywiz_api.schema_profile import SchemaProfile

Converter = Callable[[Any], Any]


@dataclass(frozen=True)
class FieldSpec:
    aliases: tuple[str, ...]
    converter: Converter | None = None
    profile_column: str | None = None


class SchemaMappedRow:
    def __init__(
        self,
        raw_row: Dict[str, Any],
        model_cls: type,
        schema_profile: SchemaProfile | None = None,
    ):
        self.raw_row = raw_row
        self.fields = self._fields_for(model_cls)
        self._field_overrides: Dict[str, FieldSpec] = {}
        self.schema_profile = schema_profile
        profile_columns = {
            field.profile_column
            for field in self.fields.values()
            if field.profile_column is not None
        }
        if schema_profile is not None and profile_columns:
            schema_profile.require_columns(*sorted(profile_columns))

    @classmethod
    def from_row(cls, row: Any, model_cls: type) -> "SchemaMappedRow":
        if isinstance(row, cls):
            return row
        return cls(row, model_cls)

    def get(self, field_name: str) -> Any:
        spec = self.fields[field_name]
        aliases = spec.aliases
        if self.schema_profile is not None and spec.profile_column is not None:
            profile_alias = getattr(self.schema_profile, spec.profile_column)
            if profile_alias is not None:
                aliases = (profile_alias,)
        for alias in aliases:
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
            f"Tried {list(aliases)}. "
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


def schema_field(
    *aliases: str,
    converter: Converter | None = None,
    profile_column: str | None = None,
) -> FieldSpec:
    return FieldSpec(
        aliases=aliases, converter=converter, profile_column=profile_column
    )


def datetime_field(*aliases: str, value_if_null: datetime | None = None) -> FieldSpec:
    def converter(raw_value: Any) -> datetime | None:
        if raw_value is None:
            return value_if_null
        return RDH.get_datetime(raw_value)

    return schema_field(*aliases, converter=converter)


def decimal_field(*aliases: str, profile_column: str | None = None) -> FieldSpec:
    return schema_field(
        *aliases, converter=RDH.get_decimal, profile_column=profile_column
    )


def nullable_decimal_field(
    *aliases: str, profile_column: str | None = None
) -> FieldSpec:
    return schema_field(
        *aliases, converter=RDH.get_nullable_decimal, profile_column=profile_column
    )


def is_one_field(*aliases: str) -> FieldSpec:
    def converter(raw_value: Any) -> bool:
        if type(raw_value) is not int or raw_value not in (0, 1):
            raise ValueError("boolean field must be stored as zero or one")
        return raw_value == 1

    return schema_field(*aliases, converter=converter)


def mapped_row(
    row: Any,
    model_cls: type,
    field_overrides: Dict[str, FieldSpec] | None = None,
    schema_profile: SchemaProfile | None = None,
) -> SchemaMappedRow:
    if isinstance(row, SchemaMappedRow):
        if schema_profile is None:
            mapped = row
        else:
            mapped = SchemaMappedRow(row.raw_row, model_cls, schema_profile)
            mapped.fields = {**mapped.fields, **row._field_overrides}
            mapped._field_overrides = dict(row._field_overrides)
    else:
        mapped = SchemaMappedRow(row, model_cls, schema_profile)
    if field_overrides:
        mapped.fields = {**mapped.fields, **field_overrides}
        mapped._field_overrides.update(field_overrides)
    return mapped
