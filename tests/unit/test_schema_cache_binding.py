from contextlib import closing
from pathlib import Path
import sqlite3

import pytest

from moneywiz_api import MoneywizApi
from moneywiz_api.database_accessor import DatabaseAccessor, DatabaseSchemaError
from moneywiz_api.schema_profile import detect_schema_profile


SCHEMA_CHANGED = "database schema changed; close and reopen the accessor"


def open_writer(path: Path):
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def create_account_store(path: Path, *, extra_metadata=()) -> None:
    connection = open_writer(path)
    connection.execute(
        "CREATE TABLE Z_PRIMARYKEY "
        "(Z_ENT INTEGER, Z_NAME TEXT, Z_SUPER INTEGER, Z_MAX INTEGER)"
    )
    connection.executemany(
        "INSERT INTO Z_PRIMARYKEY VALUES (?, ?, ?, ?)",
        [
            (8, "SyncObject", 0, 0),
            (9, "Account", 8, 0),
            (10, "CashAccount", 9, 1),
            *extra_metadata,
        ],
    )
    connection.execute(
        "CREATE TABLE ZSYNCOBJECT ("
        "Z_PK INTEGER PRIMARY KEY, Z_ENT INTEGER, ZOBJECTCREATIONDATE FLOAT, "
        "ZGID TEXT, ZDISPLAYORDER INTEGER, ZGROUPID INTEGER, ZNAME TEXT, "
        "ZCURRENCYNAME TEXT, ZOPENINGBALANCE FLOAT, ZINFO TEXT, ZUSER INTEGER)"
    )
    connection.execute(
        "INSERT INTO ZSYNCOBJECT VALUES "
        "(1, 10, 0, 'account-1', 1, 1, 'Before', 'EUR', 0, NULL, 1)"
    )
    connection.commit()
    connection.close()


def remap_cash_account(path: Path) -> None:
    connection = open_writer(path)
    connection.execute(
        "UPDATE Z_PRIMARYKEY SET Z_NAME = 'RetiredCashAccount' WHERE Z_ENT = 10"
    )
    connection.execute("INSERT INTO Z_PRIMARYKEY VALUES (11, 'CashAccount', 9, 1)")
    connection.execute(
        "UPDATE ZSYNCOBJECT SET Z_ENT = 11, ZNAME = 'After' WHERE Z_PK = 1"
    )
    connection.commit()
    connection.close()


def create_holding_store(path: Path) -> None:
    connection = open_writer(path)
    connection.execute(
        "CREATE TABLE Z_PRIMARYKEY "
        "(Z_ENT INTEGER, Z_NAME TEXT, Z_SUPER INTEGER, Z_MAX INTEGER)"
    )
    connection.executemany(
        "INSERT INTO Z_PRIMARYKEY VALUES (?, ?, ?, ?)",
        [(8, "SyncObject", 0, 0), (24, "InvestmentHolding", 8, 1)],
    )
    connection.execute(
        "CREATE TABLE ZSYNCOBJECT ("
        "Z_PK INTEGER PRIMARY KEY, Z_ENT INTEGER, ZOBJECTCREATIONDATE FLOAT, "
        "ZGID TEXT, ZINVESTMENTACCOUNT INTEGER, ZOPENNINGNUMBEROFSHARES FLOAT, "
        "ZNUMBEROFSHARES FLOAT, ZPRICEPERSHARE FLOAT, ZSYMBOL TEXT, "
        "ZHOLDINGTYPE TEXT, ZDESC TEXT, ZISPRICEPERSHAREAVAILABLEONLINE INTEGER, "
        "ZINVESTMENTOBJECTTYPE INTEGER, ZCOSTBASISOFMISSINGOBSHARES FLOAT)"
    )
    connection.execute(
        "INSERT INTO ZSYNCOBJECT VALUES "
        "(1, 24, 0, 'holding-1', 5, NULL, 2, 10, 'ACME', NULL, 'Acme', 0, 0, 0)"
    )
    connection.commit()
    connection.close()


def test_metadata_remap_refuses_and_invalidates_loaded_manager(tmp_path) -> None:
    path = tmp_path / "metadata-remap.sqlite"
    create_account_store(path)
    with closing(MoneywizApi(path, managers=("accounts",))) as api:
        manager = api.account_manager
        remap_cash_account(path)

        with pytest.raises(DatabaseSchemaError, match=f"^{SCHEMA_CHANGED}$"):
            api.load(("accounts",))

        assert api.account_manager is manager
        assert manager.records() == {}
        assert not manager.load_report.observed
        assert not api.completeness().complete
        assert not api.accessor._con.in_transaction

    with closing(MoneywizApi(path, managers=("accounts",))) as reopened:
        account = reopened.account_manager.get(1)
        assert account is not None
        assert account.name == "After"
        assert reopened.completeness().managers["accounts"].complete


@pytest.mark.parametrize("duplicate", ["id", "name"])
def test_duplicate_entity_map_keys_are_rejected(tmp_path, duplicate) -> None:
    path = tmp_path / f"duplicate-{duplicate}.sqlite"
    create_account_store(path)
    connection = open_writer(path)
    if duplicate == "id":
        connection.execute(
            "INSERT INTO Z_PRIMARYKEY VALUES (10, 'OtherCashAccount', 9, 0)"
        )
    else:
        connection.execute("INSERT INTO Z_PRIMARYKEY VALUES (11, 'CashAccount', 9, 0)")
    connection.commit()
    connection.close()

    with pytest.raises(DatabaseSchemaError, match="duplicate entity"):
        DatabaseAccessor(path)


def test_relationship_schema_change_refuses_with_equal_profile(tmp_path) -> None:
    path = tmp_path / "relationship-ddl.sqlite"
    create_account_store(path)
    with closing(DatabaseAccessor(path)) as accessor:
        profile = accessor.schema_profile
        connection = open_writer(path)
        connection.execute(
            "CREATE TABLE Z_99TAGS (Z_99TRANSACTIONS INTEGER, Z_36TAGS INTEGER)"
        )
        connection.commit()
        connection.close()
        assert detect_schema_profile(accessor._con) == profile

        with pytest.raises(DatabaseSchemaError, match=f"^{SCHEMA_CHANGED}$"):
            accessor.read_tags_map()


def test_normal_data_and_zmax_growth_reload_successfully(tmp_path) -> None:
    path = tmp_path / "growth.sqlite"
    create_account_store(path)
    with closing(MoneywizApi(path, managers=("accounts",))) as api:
        manager = api.account_manager
        connection = open_writer(path)
        connection.execute("UPDATE Z_PRIMARYKEY SET Z_MAX = 2 WHERE Z_ENT = 10")
        connection.execute("UPDATE ZSYNCOBJECT SET ZNAME = 'Edited' WHERE Z_PK = 1")
        connection.execute(
            "INSERT INTO ZSYNCOBJECT VALUES "
            "(2, 10, 0, 'account-2', 2, 1, 'Added', 'EUR', 0, NULL, 1)"
        )
        connection.commit()
        connection.close()

        api.load(("accounts",))
        report = api.account_manager.load_report

        assert api.account_manager is manager
        assert report.complete
        assert report.source_ids == (1, 2)
        edited = manager.get(1)
        added = manager.get(2)
        assert edited is not None
        assert added is not None
        assert edited.name == "Edited"
        assert added.name == "Added"


def test_initialization_race_binds_one_old_snapshot_then_refuses(tmp_path, monkeypatch):
    import moneywiz_api.database_accessor as accessor_module

    path = tmp_path / "initialization-race.sqlite"
    create_holding_store(path)
    original_detect = accessor_module.detect_schema_profile
    migration_committed = False

    def migrate_then_detect(connection):
        nonlocal migration_committed
        writer = open_writer(path)
        writer.execute(
            "ALTER TABLE ZSYNCOBJECT RENAME COLUMN ZNUMBEROFSHARES TO ZNUMBEROFSHARES1"
        )
        writer.execute(
            "ALTER TABLE ZSYNCOBJECT RENAME COLUMN ZPRICEPERSHARE TO ZPRICEPERSHARE1"
        )
        writer.execute(
            "UPDATE Z_PRIMARYKEY SET Z_NAME = 'RetiredHolding' WHERE Z_ENT = 24"
        )
        writer.execute(
            "INSERT INTO Z_PRIMARYKEY VALUES (25, 'InvestmentHolding', 8, 1)"
        )
        writer.execute("UPDATE ZSYNCOBJECT SET Z_ENT = 25")
        writer.commit()
        writer.close()
        migration_committed = True
        return original_detect(connection)

    monkeypatch.setattr(accessor_module, "detect_schema_profile", migrate_then_detect)
    accessor = DatabaseAccessor(path)

    assert migration_committed
    assert accessor.schema_profile.profile_id == "unsuffixed-investment-columns"
    assert accessor.ent_for("InvestmentHolding") == 24
    assert (24, "InvestmentHolding") in accessor._schema_identity[1]
    assert (25, "InvestmentHolding", 8) not in accessor._schema_identity[1]
    with accessor._raw_read_transaction():
        assert accessor._read_schema_identity() != accessor._schema_identity
    with pytest.raises(DatabaseSchemaError, match=f"^{SCHEMA_CHANGED}$"):
        accessor.query_objects(["InvestmentHolding"])
    accessor.close()

    monkeypatch.setattr(accessor_module, "detect_schema_profile", original_detect)
    with closing(DatabaseAccessor(path)) as reopened:
        assert reopened.schema_profile.profile_id == "suffixed-investment-columns"
        assert reopened.ent_for("InvestmentHolding") == 25


def test_reload_race_reads_old_snapshot_then_next_load_refuses(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "reload-race.sqlite"
    create_account_store(path)
    with closing(MoneywizApi(path, managers=("accounts",))) as api:
        original_verify = api.accessor._verify_schema_identity
        migration_committed = False

        def verify_then_migrate():
            nonlocal migration_committed
            original_verify()
            if not migration_committed:
                remap_cash_account(path)
                migration_committed = True

        monkeypatch.setattr(
            api.accessor, "_verify_schema_identity", verify_then_migrate
        )

        api.load(("accounts",))
        report = api.account_manager.load_report

        assert migration_committed
        assert report.complete
        assert report.source_ids == (1,)
        account = api.account_manager.get(1)
        assert account is not None
        assert account.name == "Before"
        with pytest.raises(DatabaseSchemaError, match=f"^{SCHEMA_CHANGED}$"):
            api.load(("accounts",))
        assert api.account_manager.records() == {}
        assert not api.account_manager.load_report.observed


def test_interrupted_nested_read_refuses_and_recovers(tmp_path) -> None:
    path = tmp_path / "interrupted-read.sqlite"
    create_account_store(path)

    with closing(DatabaseAccessor(path)) as accessor:
        with pytest.raises(
            DatabaseSchemaError, match="read transaction was interrupted"
        ):
            with accessor.read_transaction():
                accessor._con.rollback()
                with accessor.read_transaction():
                    pytest.fail("nested read must refuse the lost snapshot")

        assert accessor.query_objects(["CashAccount"])


def test_data_only_investment_alias_change_requires_reopening(tmp_path):
    from tests.unit.test_profiled_investment_values import investment_transaction_row
    from moneywiz_api.managers.transaction_manager import TransactionManager
    from moneywiz_api.model.transaction import InvestmentBuyTransaction

    row = investment_transaction_row(40, -20.0)
    row.update(
        ZNUMBEROFSHARES=2.0,
        ZPRICEPERSHARE=10.0,
        ZNUMBEROFSHARES1=None,
        ZPRICEPERSHARE1=None,
    )
    path = tmp_path / "data-only-alias.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE Z_PRIMARYKEY (Z_ENT INTEGER, Z_NAME TEXT, Z_SUPER INTEGER)"
        )
        connection.execute(
            "INSERT INTO Z_PRIMARYKEY VALUES (40, 'InvestmentBuyTransaction', 0)"
        )
        columns = ", ".join(f'"{column}"' for column in row)
        connection.execute(f"CREATE TABLE ZSYNCOBJECT ({columns})")
        placeholders = ", ".join("?" for _ in row)
        connection.execute(
            f"INSERT INTO ZSYNCOBJECT VALUES ({placeholders})", tuple(row.values())
        )
    with closing(DatabaseAccessor(path)) as accessor:
        original_schema = accessor._read_schema_identity()
        assert accessor.get_record(40, InvestmentBuyTransaction).number_of_shares == 2
        writer = sqlite3.connect(path)
        writer.execute(
            "UPDATE ZSYNCOBJECT SET ZNUMBEROFSHARES=NULL, ZPRICEPERSHARE=NULL, "
            "ZNUMBEROFSHARES1=2.0, ZPRICEPERSHARE1=10.0"
        )
        writer.commit()
        writer.close()
        assert accessor._read_schema_identity() == original_schema
        assert detect_schema_profile(accessor._con) != accessor.schema_profile
        with pytest.raises(DatabaseSchemaError, match="close and reopen"):
            accessor.get_record(40, InvestmentBuyTransaction)
        with pytest.raises(DatabaseSchemaError, match="close and reopen"):
            accessor.get_record_by_gid("investment-40", InvestmentBuyTransaction)
        with pytest.raises(DatabaseSchemaError, match="close and reopen"):
            TransactionManager().load(accessor)
