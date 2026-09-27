from contextlib import closing
import sqlite3

import pytest

from moneywiz_api.database_accessor import (
    DatabaseAccessor,
    DatabaseSchemaError,
)


def create_schema(path) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE Z_PRIMARYKEY "
        "(Z_ENT INTEGER PRIMARY KEY, Z_NAME TEXT, Z_SUPER INTEGER, Z_MAX INTEGER)"
    )
    connection.execute("CREATE TABLE ZSYNCOBJECT (Z_PK INTEGER, Z_ENT INTEGER)")
    connection.executemany(
        "INSERT INTO Z_PRIMARYKEY VALUES (?, ?, ?, ?)",
        [
            (8, "SyncObject", 0, 0),
            (9, "Account", 8, 0),
            (10, "CashAccount", 9, 0),
            (11, "FutureAccount", 9, 0),
            (12, "OnlineAccount", 8, 0),
        ],
    )
    connection.commit()
    connection.close()


def test_accessor_requires_an_existing_database(tmp_path) -> None:
    path = tmp_path / "missing.sqlite"
    with pytest.raises(sqlite3.OperationalError):
        DatabaseAccessor(path)
    assert not path.exists()


def test_accessor_rejects_non_moneywiz_sqlite(tmp_path) -> None:
    path = tmp_path / "other.sqlite"
    sqlite3.connect(path).close()

    with pytest.raises(DatabaseSchemaError):
        DatabaseAccessor(path)


def test_accessor_is_read_only(tmp_path) -> None:
    path = tmp_path / "moneywiz.sqlite"
    create_schema(path)

    with closing(DatabaseAccessor(path)) as accessor:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            accessor._con.execute("CREATE TABLE mutation (id INTEGER)")


def test_get_record_preserves_callable_constructors(tmp_path) -> None:
    path = tmp_path / "moneywiz.sqlite"
    create_schema(path)
    with sqlite3.connect(path) as connection:
        connection.execute("ALTER TABLE ZSYNCOBJECT ADD COLUMN ZGID TEXT")
        connection.execute("INSERT INTO ZSYNCOBJECT VALUES (1, 10, 'record-gid')")

    def get_gid(row):
        return row["ZGID"]

    with closing(DatabaseAccessor(path)) as accessor:
        assert accessor.get_record(1, get_gid) == "record-gid"
        assert accessor.get_record_by_gid("record-gid", get_gid) == "record-gid"


@pytest.mark.parametrize("columns", ["Z_NAME TEXT", "Z_ENT INTEGER"])
def test_incomplete_entity_metadata_is_rejected(tmp_path, columns) -> None:
    path = tmp_path / "malformed.sqlite"
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(f"CREATE TABLE Z_PRIMARYKEY ({columns})")
        connection.execute("CREATE TABLE ZSYNCOBJECT (Z_PK INTEGER, Z_ENT INTEGER)")
        connection.commit()

    with pytest.raises(DatabaseSchemaError):
        DatabaseAccessor(path)
