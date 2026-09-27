import sqlite3
from contextlib import closing

import pytest

from moneywiz_api import MoneywizApi


def create_read_schema(path) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE Z_PRIMARYKEY "
        "(Z_ENT INTEGER PRIMARY KEY, Z_NAME TEXT, Z_SUPER INTEGER, Z_MAX INTEGER)"
    )
    connection.executemany(
        "INSERT INTO Z_PRIMARYKEY VALUES (?, ?, ?, ?)",
        [
            (8, "SyncObject", 0, 0),
            (9, "Account", 8, 0),
            (10, "CashAccount", 9, 0),
            (35, "Tag", 8, 0),
            (36, "Transaction", 8, 0),
            (37, "DepositTransaction", 36, 0),
        ],
    )
    connection.execute(
        "CREATE TABLE ZSYNCOBJECT ("
        "Z_PK INTEGER PRIMARY KEY, Z_ENT INTEGER, ZOBJECTCREATIONDATE FLOAT, "
        "ZGID TEXT, ZDISPLAYORDER INTEGER, ZGROUPID INTEGER, ZNAME TEXT, "
        "ZCURRENCYNAME TEXT, ZOPENINGBALANCE FLOAT, ZINFO TEXT, ZUSER INTEGER, "
        "ZRECONCILED INTEGER, ZAMOUNT1 FLOAT, ZDESC2 TEXT, ZDATE1 FLOAT, "
        "ZNOTES1 TEXT, ZACCOUNT2 INTEGER, ZPAYEE2 INTEGER, "
        "ZORIGINALCURRENCY TEXT, ZORIGINALAMOUNT FLOAT, "
        "ZORIGINALEXCHANGERATE FLOAT)"
    )
    connection.execute(
        "CREATE TABLE Z_36TAGS (Z_36TRANSACTIONS INTEGER, Z_35TAGS INTEGER)"
    )
    connection.execute(
        "INSERT INTO ZSYNCOBJECT "
        "(Z_PK, Z_ENT, ZOBJECTCREATIONDATE, ZGID, ZDISPLAYORDER, ZGROUPID, "
        "ZNAME, ZCURRENCYNAME, ZOPENINGBALANCE, ZINFO, ZUSER) "
        "VALUES (1, 10, 0, 'account-1', 1, 1, 'Before', 'EUR', 0, NULL, 1)"
    )
    connection.commit()
    connection.close()


def mutate_between_loads(path) -> None:
    connection = sqlite3.connect(path)
    connection.execute("UPDATE ZSYNCOBJECT SET ZNAME = 'After' WHERE Z_PK = 1")
    connection.execute(
        "INSERT INTO ZSYNCOBJECT "
        "(Z_PK, Z_ENT, ZOBJECTCREATIONDATE, ZGID, ZRECONCILED, ZAMOUNT1, "
        "ZDESC2, ZDATE1, ZNOTES1, ZACCOUNT2, ZPAYEE2, ZORIGINALCURRENCY, "
        "ZORIGINALAMOUNT, ZORIGINALEXCHANGERATE) "
        "VALUES (2, 37, 0, 'transaction-2', 0, 5, 'Income', 0, NULL, 1, "
        "NULL, 'EUR', 5, 1)"
    )
    connection.commit()
    connection.close()


@pytest.mark.parametrize(
    ("initial_managers", "expected_managers"),
    [
        (("accounts",), ("accounts", "transactions")),
        (None, None),
    ],
)
def test_scoped_reload_refreshes_loaded_union_atomically(
    tmp_path, initial_managers, expected_managers
) -> None:
    path = tmp_path / "generation.sqlite"
    create_read_schema(path)

    with closing(MoneywizApi(path, managers=initial_managers)) as api:
        account = api.account_manager.get(1)
        assert account is not None
        assert account.name == "Before"
        assert account.info is None
        assert api.account_manager.load_report.complete
        mutate_between_loads(path)

        api.load(("transactions",))
        completeness = api.completeness()
        assert tuple(completeness.managers) == (
            expected_managers or tuple(api._managers)
        )
        account = api.account_manager.get(1)
        transaction = api.transaction_manager.get(2)
        assert account is not None
        assert transaction is not None
        assert account.name == "After"
        assert transaction.description == "Income"


def test_failed_scoped_reload_invalidates_loaded_managers(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "reload.sqlite"
    create_read_schema(path)

    with closing(MoneywizApi(path, managers=("accounts",))) as api:

        def fail(_accessor):
            raise RuntimeError("transaction load failed")

        monkeypatch.setattr(api.transaction_manager, "load", fail)
        with pytest.raises(RuntimeError, match="transaction load failed"):
            api.load(("transactions",))

        assert api.account_manager.records() == {}
        assert api.account_manager.load_report.status == "unloaded"
        assert api.transaction_manager.load_report.status == "unloaded"
        assert not api.completeness().complete
