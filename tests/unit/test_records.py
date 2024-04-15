import pytest
from moneywiz_api.model.record import Record


@pytest.fixture()
def record():
    row = {
        "Z_ENT": 1,
        "ZOBJECTCREATIONDATE": 1,
        "ZGID": "00000000-0000-0000-0000-000000000000",
        "Z_PK": 1,
        "ZCUSTOMFIELD": "SOMEVALUE",
        "ZOTHERCUSTOMFIELD10": "OTHERVALUE",
        "Z7_CUSTOMFIELDS": "ANOTHERVALUE",
    }
    return Record(row)


def test_get_column_value(record):
    assert record.get_column_value("CUSTOMFIELD") == "SOMEVALUE"
    assert record.get_column_value("OTHERCUSTOMFIELD") == "OTHERVALUE"
    assert record.get_column_value("[0-9]_CUSTOMFIELDS") == "ANOTHERVALUE"
