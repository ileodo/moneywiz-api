from moneywiz_api import DEFAULT_SCHEMA_PROFILE
import sqlite3

import pytest

from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.schema.schema_profile import TagTableInfo


def _create_accessor(db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("CREATE TABLE Z_PRIMARYKEY (Z_ENT INTEGER, Z_NAME TEXT)")
    con.commit()
    con.close()

    profile = DEFAULT_SCHEMA_PROFILE.with_tag_table_info(
        TagTableInfo(
            table_name="Z_37TAGS",
            transactions_column="Z_3TRANSACTIONS",
            tags_column="Z_4TAGS",
        )
    )
    return DatabaseAccessor(db_path, profile)


def test_get_tags_map_uses_highest_numbered_tags_table(tmp_path):
    db_path = tmp_path / "moneywiz.sqlite"
    accessor = _create_accessor(db_path)
    cur = accessor._con.cursor()
    cur.execute("CREATE TABLE Z_36TAGS (Z_1TRANSACTIONS INTEGER, Z_2TAGS INTEGER)")
    cur.execute("CREATE TABLE Z_37TAGS (Z_3TRANSACTIONS INTEGER, Z_4TAGS INTEGER)")
    cur.execute("INSERT INTO Z_36TAGS VALUES (1, 10)")
    cur.execute("INSERT INTO Z_37TAGS VALUES (2, 20)")
    cur.execute("INSERT INTO Z_37TAGS VALUES (2, 21)")
    accessor._con.commit()

    assert accessor.get_tags_map() == {2: [20, 21]}
    assert accessor.schema_profile.tag_table_info == TagTableInfo(
        table_name="Z_37TAGS",
        transactions_column="Z_3TRANSACTIONS",
        tags_column="Z_4TAGS",
    )


def test_get_tags_map_raises_when_tags_table_is_missing(tmp_path):
    db_path = tmp_path / "moneywiz.sqlite"
    accessor = _create_accessor(db_path)

    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        accessor.get_tags_map()
