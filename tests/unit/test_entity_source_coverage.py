from contextlib import closing
from pathlib import Path
import sqlite3

import pytest

from moneywiz_api.database_accessor import DatabaseAccessor, DatabaseSchemaError
from moneywiz_api.managers.account_manager import AccountManager
from moneywiz_api.managers.category_manager import CategoryManager
from moneywiz_api.managers.investment_holding_manager import (
    InvestmentHoldingManager,
)
from moneywiz_api.managers.payee_manager import PayeeManager
from moneywiz_api.managers.tag_manager import TagManager
from moneywiz_api.managers.transaction_manager import TransactionManager


UNCLASSIFIABLE = "database contains rows with unclassifiable entity ancestry"


def common_row(record_id: int, ent_id: int | None, gid: str) -> dict:
    return {
        "Z_PK": record_id,
        "Z_ENT": ent_id,
        "ZOBJECTCREATIONDATE": 0.0,
        "ZGID": gid,
    }


def account_row() -> dict:
    return {
        **common_row(1, 10, "account-1"),
        "ZDISPLAYORDER": 1,
        "ZGROUPID": 1,
        "ZNAME": "Account",
        "ZCURRENCYNAME": "EUR",
        "ZOPENINGBALANCE": 0.0,
        "ZINFO": None,
        "ZUSER": 1,
    }


MANAGER_CASES = [
    (PayeeManager, "Payee", 28, "Payee", 28),
    (CategoryManager, "Category", 19, "Category", 19),
    (InvestmentHoldingManager, "InvestmentHolding", 24, "InvestmentHolding", 24),
    (TagManager, "Tag", 35, "Tag", 35),
    (TransactionManager, "Transaction", 37, "DepositTransaction", 38),
]


PARTIALLY_MIGRATED_HIERARCHIES = [
    (TransactionManager, "Transaction", "DepositTransaction", 38),
]


def create_store(path: Path, metadata: list[tuple[int, str, int]], rows: list[dict]):
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        "CREATE TABLE Z_PRIMARYKEY "
        "(Z_ENT INTEGER, Z_NAME TEXT, Z_SUPER INTEGER, Z_MAX INTEGER)"
    )
    connection.executemany("INSERT INTO Z_PRIMARYKEY VALUES (?, ?, ?, 0)", metadata)
    columns = list(
        dict.fromkeys(
            ["Z_PK", "Z_ENT", "ZOBJECTCREATIONDATE", "ZGID"]
            + [column for row in rows for column in row]
        )
    )
    definitions = ", ".join(
        f'"{column}" INTEGER' if column in {"Z_PK", "Z_ENT"} else f'"{column}"'
        for column in columns
    )
    connection.execute(f"CREATE TABLE ZSYNCOBJECT ({definitions})")
    for row in rows:
        insert_row(connection, row)
    connection.commit()
    connection.close()


def insert_row(connection: sqlite3.Connection, row: dict) -> None:
    columns = tuple(row)
    names = ", ".join(f'"{column}"' for column in columns)
    placeholders = ", ".join("?" for _ in columns)
    connection.execute(
        f"INSERT INTO ZSYNCOBJECT ({names}) VALUES ({placeholders})",
        tuple(row[column] for column in columns),
    )


@pytest.mark.parametrize(
    ("manager_type", "root_name", "root_id", "known_name", "known_id"),
    MANAGER_CASES,
)
@pytest.mark.parametrize("transitive", [False, True], ids=["direct", "transitive"])
def test_managers_count_unknown_descendants(
    tmp_path,
    manager_type,
    root_name,
    root_id,
    known_name,
    known_id,
    transitive,
) -> None:
    path = tmp_path / f"{root_name}-{transitive}.sqlite"
    metadata = [(8, "SyncObject", 0), (root_id, root_name, 8)]
    if known_id != root_id:
        metadata.append((known_id, known_name, root_id))
    unknown_parent = root_id
    if transitive:
        metadata.append((90, f"Future{root_name}Parent", root_id))
        unknown_parent = 90
    unknown_name = f"Future{root_name}"
    metadata.append((91, unknown_name, unknown_parent))
    create_store(path, metadata, [common_row(2, 91, "future")])

    with closing(DatabaseAccessor(path)) as accessor:
        report = manager_type().load(accessor)

    assert report.source_ids == (2,)
    assert report.parsed_ids == ()
    assert len(report.skipped) == 1
    assert report.skipped[0].record_id == 2
    assert report.skipped[0].entity == unknown_name
    assert report.skipped[0].error.value == "unknown_entity"


@pytest.mark.parametrize(
    ("manager_type", "missing_root", "known_name", "known_id"),
    PARTIALLY_MIGRATED_HIERARCHIES,
)
def test_unknown_descendant_is_counted_when_abstract_root_is_absent(
    tmp_path,
    manager_type,
    missing_root,
    known_name,
    known_id,
) -> None:
    path = tmp_path / f"missing-{missing_root}.sqlite"
    future_name = f"Future{known_name}"
    create_store(
        path,
        [
            (8, "SyncObject", 0),
            (known_id, known_name, 8),
            (91, future_name, known_id),
        ],
        [common_row(2, 91, "future")],
    )

    with closing(DatabaseAccessor(path)) as accessor:
        report = manager_type().load(accessor)

    assert report.source_ids == (2,)
    assert report.parsed_ids == ()
    assert len(report.skipped) == 1
    assert report.skipped[0].record_id == 2
    assert report.skipped[0].entity == future_name
    assert report.skipped[0].error.value == "unknown_entity"
    assert not report.complete


def orphan_metadata(kind: str) -> tuple[list[tuple[int, str, int]], int | None]:
    metadata = [(8, "SyncObject", 0), (9, "Account", 8), (10, "CashAccount", 9)]
    if kind == "null":
        return metadata, None
    if kind == "unmapped":
        return metadata, 99
    if kind == "missing-parent":
        return [*metadata, (90, "FuturePayee", 99)], 90
    if kind == "cycle":
        return [*metadata, (90, "FuturePayee", 91), (91, "FuturePayeeParent", 90)], 90
    raise AssertionError("unsupported synthetic orphan kind")


@pytest.mark.parametrize("kind", ["null", "unmapped", "missing-parent", "cycle"])
def test_unclassifiable_observed_entity_refuses_source_read(tmp_path, kind) -> None:
    path = tmp_path / f"{kind}.sqlite"
    metadata, ent_id = orphan_metadata(kind)
    create_store(path, metadata, [account_row(), common_row(2, ent_id, "orphan")])

    with closing(DatabaseAccessor(path)) as accessor:
        with pytest.raises(DatabaseSchemaError, match=f"^{UNCLASSIFIABLE}$"):
            accessor.query_objects(["CashAccount"])


def test_unobserved_broken_metadata_and_absent_optional_roots_are_allowed(
    tmp_path,
) -> None:
    path = tmp_path / "unused-broken-metadata.sqlite"
    create_store(path, [(8, "SyncObject", 0), (90, "FutureUnused", 99)], [])

    with closing(DatabaseAccessor(path)) as accessor:
        reports = [
            manager_type().load(accessor)
            for manager_type in (
                AccountManager,
                PayeeManager,
                CategoryManager,
                TransactionManager,
                InvestmentHoldingManager,
                TagManager,
            )
        ]

    assert all(report.source_count == 0 and report.complete for report in reports)


def test_known_unrelated_malformed_row_does_not_block_account_scope(tmp_path) -> None:
    path = tmp_path / "known-unrelated.sqlite"
    metadata = [
        (8, "SyncObject", 0),
        (9, "Account", 8),
        (10, "CashAccount", 9),
        (80, "KnownUnrelated", 8),
    ]
    create_store(path, metadata, [account_row(), common_row(2, 80, "unrelated")])

    with closing(DatabaseAccessor(path)) as accessor:
        report = AccountManager().load(accessor)

    assert report.complete
    assert report.source_ids == (1,)
    assert report.parsed_ids == (1,)


def test_invalid_account_display_order_is_reported_before_sorting(tmp_path) -> None:
    path = tmp_path / "invalid-display-order.sqlite"
    metadata = [(8, "SyncObject", 0), (9, "Account", 8), (10, "CashAccount", 9)]
    invalid = {**account_row(), "ZDISPLAYORDER": "PRIVATE_PAYLOAD"}
    valid = {**account_row(), "Z_PK": 2, "ZGID": "account-2", "ZDISPLAYORDER": 2}
    create_store(path, metadata, [invalid, valid])

    with closing(DatabaseAccessor(path)) as accessor:
        manager = AccountManager()
        report = manager.load(accessor)

    assert not report.complete
    assert report.parsed_ids == (2,)
    assert report.skipped[0].error.value == "validation"
    assert list(manager.records()) == [2]
