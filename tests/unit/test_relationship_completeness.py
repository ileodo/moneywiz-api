from contextlib import closing
import json
import sqlite3

import pytest

from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.managers.transaction_manager import TransactionManager
from moneywiz_api.read_result import RelationshipStorage


def create_relationship_schema(path, *, include_tables=True) -> None:
    create_custom_relationship_schema(
        path,
        metadata=(
            (2, "CategoryAssigment", 0, 0),
            (8, "SyncObject", 0, 0),
            (36, "Tag", 8, 0),
            (37, "Transaction", 8, 0),
            (50, "WithdrawRefundTransactionLink", 0, 0),
        ),
        tables=(
            "CREATE TABLE ZCATEGORYASSIGMENT "
            "(Z_PK INTEGER PRIMARY KEY, ZCATEGORY INTEGER, ZAMOUNT FLOAT, "
            "ZTRANSACTION INTEGER)",
            "CREATE TABLE ZWITHDRAWREFUNDTRANSACTIONLINK "
            "(Z_PK INTEGER PRIMARY KEY, ZREFUNDTRANSACTION INTEGER, "
            "ZWITHDRAWTRANSACTION INTEGER)",
            "CREATE TABLE Z_37TAGS (Z_37TRANSACTIONS INTEGER, Z_36TAGS INTEGER)",
        )
        if include_tables
        else (),
    )
    if include_tables:
        connection = sqlite3.connect(path)
        connection.executemany(
            "INSERT INTO ZCATEGORYASSIGMENT VALUES (?, ?, ?, ?)",
            [
                (1, 10, 5.0, 100),
                (2, 11, None, 101),
                (3, 12, 2.0, None),
                (6, "PRIVATE_PAYLOAD", 3.0, 102),
            ],
        )
        connection.executemany(
            "INSERT INTO ZWITHDRAWREFUNDTRANSACTIONLINK VALUES (?, ?, ?)",
            [(4, 102, 103), (5, 104, None)],
        )
        connection.executemany(
            "INSERT INTO Z_37TAGS VALUES (?, ?)",
            [(100, 200), (101, None)],
        )
        connection.commit()
        connection.close()


def create_custom_relationship_schema(path, metadata=(), tables=()) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE Z_PRIMARYKEY "
        "(Z_ENT INTEGER PRIMARY KEY, Z_NAME TEXT, Z_SUPER INTEGER, Z_MAX INTEGER)"
    )
    connection.execute("CREATE TABLE ZSYNCOBJECT (Z_PK INTEGER, Z_ENT INTEGER)")
    connection.executemany("INSERT INTO Z_PRIMARYKEY VALUES (?, ?, ?, ?)", metadata)
    for statement in tables:
        connection.execute(statement)
    connection.commit()
    connection.close()


def read_tags(path):
    with closing(DatabaseAccessor(path)) as accessor:
        tags, report = accessor.read_tags_map()
    return tags, report


def test_shifted_relationship_layouts_report_valid_and_skipped_rows(tmp_path) -> None:
    path = tmp_path / "relationships.sqlite"
    create_relationship_schema(path)

    with closing(DatabaseAccessor(path)) as accessor:
        categories, category_report = accessor.read_category_assignments()
        refunds, refund_report = accessor.read_refund_maps()
        tags, tag_report = accessor.read_tags_map()

        assert categories == {100: [(10, 5)]}
        assert category_report.source_count == 3
        assert category_report.parsed_count == 1
        assert category_report.status == "partial"
        assert "PRIVATE_PAYLOAD" not in json.dumps(category_report.as_dict())
        assert refunds == {102: 103}
        assert refund_report.source_count == 2
        assert refund_report.parsed_count == 1
        assert refund_report.status == "partial"
        assert tags == {100: [200]}
        assert tag_report.storage_name == "Z_37TAGS"
        assert tag_report.source_count == 2
        assert tag_report.parsed_count == 1
        assert tag_report.skipped[0].record_id == "row:1"
        assert tag_report.status == "partial"

        manager_report = TransactionManager().load(accessor)

    assert manager_report.status == "partial"
    assert not manager_report.complete
    assert set(manager_report.relationships) == {
        "category_assignments",
        "refund_links",
        "transaction_tags",
    }
    assert (
        manager_report.as_dict()["relationships"]["transaction_tags"]["storage_name"]
        == "Z_37TAGS"
    )


def test_category_counts_exclude_supported_nontransaction_owners(tmp_path) -> None:
    path = tmp_path / "nontransaction-category-owners.sqlite"
    create_custom_relationship_schema(
        path,
        metadata=((2, "CategoryAssigment", 0, 0),),
        tables=(
            "CREATE TABLE ZCATEGORYASSIGMENT "
            "(Z_PK INTEGER, ZCATEGORY INTEGER, ZAMOUNT FLOAT, "
            "ZTRANSACTION INTEGER, ZBUDGET INTEGER, "
            "ZSCHEDULEDTRANSACITION INTEGER, ZSTRINGHISTORYITEM INTEGER)",
        ),
    )
    with sqlite3.connect(path) as connection:
        connection.executemany(
            "INSERT INTO ZCATEGORYASSIGMENT VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (1, 10, 5.0, 100, None, None, None),
                (2, 11, 2.0, None, 200, None, None),
                (3, 12, 3.0, None, None, 300, None),
                (4, 13, 4.0, None, None, None, 400),
            ],
        )

    with closing(DatabaseAccessor(path)) as accessor:
        categories, report = accessor.read_category_assignments()

    assert categories == {100: [(10, 5)]}
    assert report.source_count == 1
    assert report.parsed_count == 1
    assert report.complete


def test_known_entity_with_missing_storage_is_unknown(tmp_path) -> None:
    path = tmp_path / "missing-storage.sqlite"
    create_relationship_schema(path, include_tables=False)

    with closing(DatabaseAccessor(path)) as accessor:
        results = (
            accessor.read_category_assignments(),
            accessor.read_refund_maps(),
            accessor.read_tags_map(),
        )
        manager_report = TransactionManager().load(accessor)

    assert all(data == {} for data, _ in results)
    assert all(
        report.storage == RelationshipStorage.UNKNOWN and not report.complete
        for _, report in results
    )
    assert manager_report.status == "error"
    assert not manager_report.complete


def test_missing_optional_relationship_entities_are_absent(tmp_path) -> None:
    path = tmp_path / "absent-relationships.sqlite"
    create_custom_relationship_schema(path)

    with closing(DatabaseAccessor(path)) as accessor:
        reports = [
            accessor.read_category_assignments()[1],
            accessor.read_refund_maps()[1],
            accessor.read_tags_map()[1],
        ]
        manager_report = TransactionManager().load(accessor)

    assert all(report.storage == RelationshipStorage.ABSENT for report in reports)
    assert all(report.complete for report in reports)
    assert manager_report.complete


@pytest.mark.parametrize(
    ("reader_name", "table_statement"),
    [
        (
            "read_category_assignments",
            "CREATE TABLE ZCATEGORYASSIGMENT "
            "(Z_PK INTEGER, ZCATEGORY INTEGER, ZTRANSACTION INTEGER, ZAMOUNT FLOAT)",
        ),
        (
            "read_tags_map",
            "CREATE TABLE Z_37TAGS (Z_37TRANSACTIONS INTEGER, Z_36TAGS INTEGER)",
        ),
    ],
)
def test_physical_storage_without_metadata_is_unknown(
    tmp_path, reader_name, table_statement
) -> None:
    path = tmp_path / f"{reader_name}-physical-only.sqlite"
    create_custom_relationship_schema(path, tables=(table_statement,))

    with closing(DatabaseAccessor(path)) as accessor:
        data, report = getattr(accessor, reader_name)()

    assert data == {}
    assert report.storage == RelationshipStorage.UNKNOWN
    assert report.status == "error"
    assert not report.complete


@pytest.mark.parametrize(
    ("reader_name", "metadata", "table_statement", "expected_storage"),
    [
        (
            "read_category_assignments",
            ((2, "CategoryAssigment", 0, 0),),
            "CREATE TABLE ZCATEGORYASSIGMENT "
            "(Z_PK INTEGER, ZCATEGORY INTEGER, ZTRANSACTION INTEGER, ZAMOUNT FLOAT)",
            RelationshipStorage.PRESENT,
        ),
        (
            "read_tags_map",
            ((36, "Tag", 0, 0), (37, "Transaction", 0, 0)),
            "CREATE TABLE Z_37TAGS (Z_37TRANSACTIONS INTEGER, Z_36TAGS INTEGER)",
            RelationshipStorage.PRESENT,
        ),
        (
            "read_category_assignments",
            ((2, "CategoryAssigment", 0, 0),),
            "CREATE TABLE ZCATEGORYASSIGMENT "
            "(Z_PK INTEGER, ZCATEGORY INTEGER, ZTRANSACTION INTEGER)",
            RelationshipStorage.UNKNOWN,
        ),
        (
            "read_tags_map",
            ((36, "Tag", 0, 0), (37, "Transaction", 0, 0)),
            "CREATE TABLE Z_37TAGS (Z_37TRANSACTIONS INTEGER)",
            RelationshipStorage.UNKNOWN,
        ),
    ],
)
def test_empty_relationship_storage_requires_expected_columns(
    tmp_path, reader_name, metadata, table_statement, expected_storage
) -> None:
    path = tmp_path / f"{reader_name}-{expected_storage.value}.sqlite"
    create_custom_relationship_schema(
        path, metadata=metadata, tables=(table_statement,)
    )

    with closing(DatabaseAccessor(path)) as accessor:
        data, report = getattr(accessor, reader_name)()

    assert data == {}
    assert report.storage == expected_storage
    assert report.complete == (expected_storage == RelationshipStorage.PRESENT)


@pytest.mark.parametrize(
    ("alternate_table", "include_expected"),
    [
        (
            "CREATE TABLE Z_36TAGS (Z_36TRANSACTIONS INTEGER, Z_35TAGS INTEGER)",
            False,
        ),
        (
            "CREATE TABLE Z_99TAGS (Z_99TRANSACTIONS INTEGER, Z_36TAGS INTEGER)",
            True,
        ),
    ],
)
def test_wrong_or_conflicting_transaction_tag_layout_is_unknown(
    tmp_path, alternate_table, include_expected
) -> None:
    path = tmp_path / "conflicting-tags.sqlite"
    expected_table = (
        "CREATE TABLE Z_37TAGS (Z_37TRANSACTIONS INTEGER, Z_36TAGS INTEGER)"
    )
    tables = (
        (expected_table, alternate_table) if include_expected else (alternate_table,)
    )
    create_custom_relationship_schema(
        path,
        metadata=((36, "Tag", 0, 0), (37, "Transaction", 0, 0)),
        tables=tables,
    )

    with closing(DatabaseAccessor(path)) as accessor:
        tags, report = accessor.read_tags_map()

    assert tags == {}
    assert report.storage == RelationshipStorage.UNKNOWN
    assert not report.complete


@pytest.mark.parametrize(
    ("info_id", "scheduled_id", "tag_id", "transaction_id"),
    [(23, 31, 35, 36), (24, 32, 36, 37)],
)
def test_unrelated_tag_tables_do_not_hide_transaction_tags(
    tmp_path, info_id, scheduled_id, tag_id, transaction_id
) -> None:
    path = tmp_path / "unrelated-tags.sqlite"
    create_custom_relationship_schema(
        path,
        metadata=(
            (info_id, "InfoCard", 0, 0),
            (scheduled_id, "ScheduledTransaction", 0, 0),
            (tag_id, "Tag", 0, 0),
            (transaction_id, "Transaction", 0, 0),
        ),
        tables=(
            f"CREATE TABLE Z_{info_id}TAGS (Z_{info_id}INFOCARDS5 INTEGER, Z_{tag_id}TAGS1 INTEGER)",
            f"CREATE TABLE Z_{scheduled_id}TAGS (Z_{scheduled_id}SCHEDULEDTRANSACTIONS1 INTEGER, Z_{tag_id}TAGS2 INTEGER)",
            f"CREATE TABLE Z_{transaction_id}TAGS (Z_{transaction_id}TRANSACTIONS INTEGER, Z_{tag_id}TAGS INTEGER)",
        ),
    )
    with sqlite3.connect(path) as connection:
        connection.execute(f"INSERT INTO Z_{info_id}TAGS VALUES (101, 201)")
        connection.execute(f"INSERT INTO Z_{scheduled_id}TAGS VALUES (102, 202)")
        connection.execute(f"INSERT INTO Z_{transaction_id}TAGS VALUES (103, 203)")
    tags, report = read_tags(path)
    assert tags == {103: [203]}
    assert report.storage == RelationshipStorage.PRESENT
    assert report.storage_name == f"Z_{transaction_id}TAGS"
    assert report.complete
