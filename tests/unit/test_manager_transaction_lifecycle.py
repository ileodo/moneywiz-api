from contextlib import closing
from decimal import Decimal
import sqlite3

from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.managers.transaction_manager import TransactionManager


def _create_wal_transaction_store(path) -> None:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        "CREATE TABLE Z_PRIMARYKEY "
        "(Z_ENT INTEGER, Z_NAME TEXT, Z_SUPER INTEGER, Z_MAX INTEGER)"
    )
    connection.executemany(
        "INSERT INTO Z_PRIMARYKEY VALUES (?, ?, ?, 0)",
        [
            (2, "CategoryAssigment", 0),
            (8, "SyncObject", 0),
            (35, "Tag", 8),
            (36, "Transaction", 8),
            (37, "DepositTransaction", 36),
            (50, "WithdrawRefundTransactionLink", 0),
        ],
    )
    connection.execute(
        "CREATE TABLE ZSYNCOBJECT ("
        "Z_PK INTEGER, Z_ENT INTEGER, ZOBJECTCREATIONDATE FLOAT, ZGID TEXT, "
        "ZRECONCILED INTEGER, ZAMOUNT1 FLOAT, ZDESC2 TEXT, ZDATE1 FLOAT, "
        "ZNOTES1 TEXT, ZACCOUNT2 INTEGER, ZPAYEE2 INTEGER, "
        "ZORIGINALCURRENCY TEXT, ZORIGINALAMOUNT FLOAT, "
        "ZORIGINALEXCHANGERATE FLOAT)"
    )
    connection.execute(
        "INSERT INTO ZSYNCOBJECT VALUES "
        "(100, 37, 0, 'transaction-100', 0, 5, 'old', 0, NULL, 1, NULL, "
        "'EUR', 5, 1)"
    )
    connection.execute(
        "CREATE TABLE ZCATEGORYASSIGMENT "
        "(Z_PK INTEGER, ZCATEGORY INTEGER, ZTRANSACTION INTEGER, ZAMOUNT FLOAT)"
    )
    connection.execute("INSERT INTO ZCATEGORYASSIGMENT VALUES (1, 7, 100, 5)")
    connection.execute(
        "CREATE TABLE ZWITHDRAWREFUNDTRANSACTIONLINK "
        "(Z_PK INTEGER, ZREFUNDTRANSACTION INTEGER, ZWITHDRAWTRANSACTION INTEGER)"
    )
    connection.execute("INSERT INTO ZWITHDRAWREFUNDTRANSACTIONLINK VALUES (2, 100, 90)")
    connection.execute(
        "CREATE TABLE Z_36TAGS (Z_36TRANSACTIONS INTEGER, Z_35TAGS INTEGER)"
    )
    connection.execute("INSERT INTO Z_36TAGS VALUES (100, 9)")
    connection.commit()
    connection.close()


def _mutate_wal_transaction_store(path) -> None:
    connection = sqlite3.connect(path)
    connection.execute("UPDATE ZSYNCOBJECT SET ZAMOUNT1 = 6, ZORIGINALAMOUNT = 6")
    connection.execute("UPDATE ZCATEGORYASSIGMENT SET ZAMOUNT = 7")
    connection.execute(
        "UPDATE ZWITHDRAWREFUNDTRANSACTIONLINK SET ZWITHDRAWTRANSACTION = 91"
    )
    connection.execute("UPDATE Z_36TAGS SET Z_35TAGS = 10")
    connection.commit()
    connection.close()


def test_direct_transaction_manager_load_uses_one_wal_generation(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "manager-generation.sqlite"
    _create_wal_transaction_store(path)

    with closing(DatabaseAccessor(path)) as accessor:
        method_name = "read_category_assignments"
        original = getattr(accessor, method_name)
        mutated = False

        def read_then_mutate(*args, **kwargs):
            nonlocal mutated
            result = original(*args, **kwargs)
            if not mutated:
                _mutate_wal_transaction_store(path)
                mutated = True
            return result

        monkeypatch.setattr(accessor, method_name, read_then_mutate)
        manager = TransactionManager()
        report = manager.load(accessor)

    assert report.complete
    assert all(item.complete for item in report.relationships.values())
    transaction = manager.get(100)
    assert transaction is not None
    assert transaction.amount == Decimal("5.0")
    assert manager.category_assignment == {100: [(7, Decimal("5.0"))]}
    assert manager.refund_maps == {100: 90}
    assert manager.tags_map == {100: [9]}
