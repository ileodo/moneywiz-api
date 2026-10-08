"""Field definitions for each model in a MoneyWiz database schema."""

from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields
from inspect import signature
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Iterable, Mapping, TypeVar, cast

if TYPE_CHECKING:
    from moneywiz_api.model.record import Record

from moneywiz_api.schema.schema_fields import FieldSpec

ColumnMap = Mapping[str | type, Mapping[str, FieldSpec]]
RecordT = TypeVar("RecordT", bound="Record")


def get_all_record_subclasses() -> list[type["Record"]]:
    """Return Record and every subclass currently loaded in the process."""
    from moneywiz_api.model.record import Record

    discovered = {Record}
    pending = [Record]
    while pending:
        for subclass in pending.pop().__subclasses__():
            if subclass not in discovered:
                discovered.add(subclass)
                pending.append(subclass)
    return sorted(discovered, key=lambda cls: cls.__name__)


@dataclass(frozen=True)
class TagTableInfo:
    table_name: str
    transactions_column: str
    tags_column: str


class SchemaProfile:
    """A per-model schema, resolved in base-to-subclass inheritance order.

    ``column_map`` keys may be model classes or their names. Each entry defines that class's
    own fields; inherited fields are supplied by the entries for its bases.
    """

    def __init__(
        self,
        column_map: ColumnMap,
        tag_table_info: TagTableInfo | None = None,
    ):
        self.column_map: ColumnMap = cast(
            ColumnMap,
            MappingProxyType(
                {
                    (key if isinstance(key, str) else key.__name__): MappingProxyType(
                        dict(value)
                    )
                    for key, value in column_map.items()
                }
            ),
        )
        self.tag_table_info = tag_table_info

    def with_tag_table_info(self, tag_table_info: TagTableInfo) -> "SchemaProfile":
        """Return this column map with tag-join table details resolved from a database."""
        return SchemaProfile(self.column_map, tag_table_info)

    def create_record(
        self, row: Mapping[str, Any], model_cls: type[RecordT]
    ) -> RecordT:
        """Create a model instance populated from a raw database row."""
        field_values: dict[str, Any] = {}
        errors: list[tuple[str, Exception]] = []
        for field in dataclass_fields(model_cls):
            field_name = field.name
            if field_name.startswith("_"):
                continue
            try:
                field_values[field_name] = self._get_field(row, model_cls, field_name)
            except Exception as error:
                errors.append((field_name, error))

        if errors:
            details = "; ".join(
                f"{field_name}: {error}" for field_name, error in errors
            )
            raise RuntimeError(
                f"Failed to resolve fields for {model_cls.__name__}: {details}"
            ) from errors[0][1]
        if tuple(signature(model_cls).parameters)[:2] == ("row", "field_values"):
            return model_cls(row, field_values)

        # Plain dataclass subclasses receive a generated initializer that does
        # not accept the raw row and resolved field mapping.
        from moneywiz_api.model.record import Record

        record = model_cls.__new__(model_cls)
        Record.__init__(record, row, field_values)
        return record

    def _get_field(
        self, row: Mapping[str, Any], model_cls: type, field_name: str
    ) -> Any:
        spec = self.specs_for(model_cls)[field_name]
        for alias in spec.aliases:
            if alias in row:
                value = row[alias]
                if spec.converter is not None:
                    try:
                        return spec.converter(value)
                    except Exception as error:
                        from moneywiz_api.schema.raw_data_handler import RawDataHandler

                        raise RuntimeError(
                            f"Failed to convert field {field_name} using column {alias} "
                            f"with value {value}, the exception was: {error}. "
                            f"the row was: {RawDataHandler.filter_row(dict(row))}"
                        ) from error
                return value
        raise KeyError(
            f"Could not resolve field {field_name}. Tried {list(spec.aliases)}. "
            f"Available columns: {list(row.keys())}"
        )

    def specs_for(self, model_cls: type) -> dict[str, FieldSpec]:
        fields: dict[str, FieldSpec] = {}
        for cls in reversed(model_cls.mro()):
            fields.update(self.column_map.get(cls.__name__, {}))
        return fields

    def validate(self, model_classes: Iterable[type["Record"]] | None = None) -> None:
        """Raise ValueError for public dataclass fields without definitions.

        By default, check Record and all currently loaded subclasses. An explicit
        iterable restricts validation to those models. Inherited definitions count,
        and fields whose names begin with an underscore are ignored.
        """
        if model_classes is None:
            model_classes = get_all_record_subclasses()

        missing: list[str] = []
        for model_cls in model_classes:
            definitions = self.specs_for(model_cls)
            missing.extend(
                f"{model_cls.__name__}.{field.name}"
                for field in dataclass_fields(model_cls)
                if not field.name.startswith("_") and field.name not in definitions
            )
        if missing:
            raise ValueError("Missing schema field definitions: " + ", ".join(missing))
