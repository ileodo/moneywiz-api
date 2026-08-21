from datetime import datetime

from moneywiz_api.model.raw_data_handler import RawDataHandler as RDH
from moneywiz_api.model.record import Record


def test_get_decimal():
    assert str(RDH.get_decimal(1.23)) == "1.23"


def test_get_nullable_decimal_none():
    assert RDH.get_nullable_decimal(None) is None


def test_get_datetime_epoch():
    dt = RDH.get_datetime(0.0)
    # Apple epoch offset should yield a datetime around 2001-01-01
    assert dt.year == 2001


def test_record_defaults_missing_creation_date_to_apple_epoch():
    record = Record(
        {
            "Z_ENT": 1,
            "ZOBJECTCREATIONDATE": None,
            "ZGID": "sanitized-example",
            "Z_PK": 1,
        }
    )

    assert record._created_at == datetime(2001, 1, 1)
