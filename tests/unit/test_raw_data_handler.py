from dataclasses import dataclass
from datetime import datetime

from moneywiz_api.schema.raw_data_handler import RawDataHandler as RDH
from moneywiz_api.model.record import Record
from moneywiz_api import DEFAULT_SCHEMA_PROFILE
from moneywiz_api.schema.schema_fields import datetime_field
from moneywiz_api.schema.schema_profile import SchemaProfile


def test_get_decimal():
    assert str(RDH.get_decimal(1.23)) == "1.23"


def test_get_nullable_decimal_none():
    assert RDH.get_nullable_decimal(None) is None


def test_get_datetime_epoch():
    dt = RDH.get_datetime(0.0)
    # Apple epoch offset should yield a datetime around 2001-01-01
    assert dt.year == 2001


def test_record_defaults_missing_creation_date_to_apple_epoch():
    record = DEFAULT_SCHEMA_PROFILE.create_record(
        {
            "Z_ENT": 1,
            "ZOBJECTCREATIONDATE": None,
            "ZGID": "sanitized-example",
            "Z_PK": 1,
        },
        Record,
    )

    assert record.created_at == datetime(2001, 1, 1)


def test_datetime_field_uses_configured_value_for_null():
    fallback = datetime(2001, 1, 1)

    @dataclass
    class TimestampedRow(Record):
        timestamp: datetime

    profile = SchemaProfile(
        {
            **DEFAULT_SCHEMA_PROFILE.column_map,
            TimestampedRow: {
                "timestamp": datetime_field("ZDATE", value_if_null=fallback)
            },
        }
    )

    record = profile.create_record(
        {
            "Z_ENT": 1,
            "ZOBJECTCREATIONDATE": 0,
            "ZGID": "gid",
            "Z_PK": 1,
            "ZDATE": None,
        },
        TimestampedRow,
    )
    assert record.timestamp == fallback
