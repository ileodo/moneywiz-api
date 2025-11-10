from moneywiz_api.model.raw_data_handler import RawDataHandler as RDH


def test_get_decimal():
    assert str(RDH.get_decimal(1.23)) == "1.23"


def test_get_nullable_decimal_none():
    assert RDH.get_nullable_decimal(None) is None


def test_get_datetime_epoch():
    dt = RDH.get_datetime(0.0)
    # Apple epoch offset should yield a datetime around 2001-01-01
    assert dt.year == 2001
