import re
import sqlite3
from collections import defaultdict
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple, cast

from moneywiz_api.model.raw_data_handler import RawDataHandler as RDH
from moneywiz_api.model.record import Record
from moneywiz_api.model.schema_mapped_row import mapped_row
from moneywiz_api.read_result import (
    LoadErrorKind,
    RelationshipLoadReport,
    RelationshipStorage,
    SkippedRecord,
)
from moneywiz_api.schema_profile import SchemaProfile, detect_schema_profile
from moneywiz_api.types import ENT_ID, GID, ID


class DatabaseSchemaError(ValueError):
    """Raised when a readable SQLite file is not a supported MoneyWiz store."""


def require_integer_identity(value: object) -> None:
    """Require an uncoerced integer identity."""
    if type(value) is not int:
        raise AssertionError()


class DatabaseAccessor:
    def __init__(self, db_path: Path):
        self._con = sqlite3.connect(
            f"{Path(db_path).expanduser().resolve().as_uri()}?mode=ro", uri=True
        )

        def dict_factory(cursor, row):
            record = {}
            for idx, col in enumerate(cursor.description):
                record[col[0]] = row[idx]
            return record

        try:
            self._con.row_factory = dict_factory
            self._initialize_schema_cache()
        except BaseException:
            self._con.close()
            raise

    def _initialize_schema_cache(self) -> None:
        """Bind all schema-dependent caches from one SQLite snapshot."""
        self._admission_depth = 0
        with self._raw_read_transaction():
            if not self._table_exists("Z_PRIMARYKEY") or not self._table_exists(
                "ZSYNCOBJECT"
            ):
                raise DatabaseSchemaError(
                    "database is missing required MoneyWiz schema tables"
                )
            required_metadata_columns = {"Z_ENT", "Z_NAME"}
            if not required_metadata_columns.issubset(
                self._table_columns("Z_PRIMARYKEY")
            ):
                raise DatabaseSchemaError(
                    "Z_PRIMARYKEY is missing required entity metadata columns"
                )
            schema_identity = self._read_schema_identity()
            schema_profile = detect_schema_profile(self._con)

        self._schema_identity = schema_identity
        self._schema_profile = schema_profile
        metadata = schema_identity[1]
        self._ent_to_typename = {ent_id: name for ent_id, name in metadata}
        self._typename_to_ent = {name: ent_id for ent_id, name in metadata}

    def _read_entity_metadata(self) -> tuple[tuple[int, str], ...]:
        cur = self._con.cursor()
        res = cur.execute(
            """
        SELECT Z_ENT, Z_NAME
        FROM "Z_PRIMARYKEY"
        ORDER BY Z_ENT
        """
        )
        rows: list[tuple[int, str]] = []
        ent_ids: set[int] = set()
        typenames: set[str] = set()
        for row in res.fetchall():
            ent_id = row["Z_ENT"]
            typename = row["Z_NAME"]
            if (
                not isinstance(ent_id, int)
                or not isinstance(typename, str)
                or not typename
            ):
                raise DatabaseSchemaError("Z_PRIMARYKEY contains invalid metadata")
            if ent_id in ent_ids:
                raise DatabaseSchemaError("Z_PRIMARYKEY contains duplicate entity IDs")
            if typename in typenames:
                raise DatabaseSchemaError(
                    "Z_PRIMARYKEY contains duplicate entity names"
                )
            ent_ids.add(ent_id)
            typenames.add(typename)
            rows.append((ent_id, typename))
        return tuple(rows)

    def _read_schema_identity(
        self,
    ) -> tuple[int, tuple[tuple[int, str], ...]]:
        schema_version = self._con.execute("PRAGMA schema_version").fetchone()[
            "schema_version"
        ]
        return schema_version, self._read_entity_metadata()

    def __repr__(self):
        return "\n".join(
            f"{key}: {value}" for key, value in self._ent_to_typename.items()
        )

    @property
    def schema_profile(self) -> SchemaProfile:
        """Return the physical-column compatibility profile for this store."""
        return self._schema_profile

    def typename_for(self, ent_id: ENT_ID) -> str:
        typename = self._ent_to_typename.get(ent_id)
        assert typename is not None, f"Unknown ent_id {ent_id}"
        return typename

    def ent_for(self, typename: str) -> ENT_ID:
        ent_id = self._typename_to_ent.get(typename)
        assert ent_id is not None, f"Unknown typename {typename}"
        return ent_id

    def _table_exists(self, table_name: str) -> bool:
        row = self._con.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        return row is not None

    def _table_columns(self, table_name: str) -> set[str]:
        return {
            str(row["name"])
            for row in self._con.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()
        }

    def _relationship_storage(
        self,
        *,
        entity_name: str,
        table_name: str,
        required_columns: tuple[str, ...],
    ) -> RelationshipStorage:
        metadata_present = entity_name in self._typename_to_ent
        table_present = self._table_exists(table_name)
        if not metadata_present and not table_present:
            return RelationshipStorage.ABSENT
        if not metadata_present or not table_present:
            return RelationshipStorage.UNKNOWN
        if not set(required_columns).issubset(self._table_columns(table_name)):
            return RelationshipStorage.UNKNOWN
        return RelationshipStorage.PRESENT

    def _transaction_tag_storage(
        self,
    ) -> tuple[RelationshipStorage, str | None, str | None, str | None]:
        transaction_ent = self._typename_to_ent.get("Transaction")
        tag_ent = self._typename_to_ent.get("Tag")
        table_name = f"Z_{transaction_ent}TAGS" if transaction_ent is not None else None
        transaction_column = (
            f"Z_{transaction_ent}TRANSACTIONS" if transaction_ent is not None else None
        )
        tag_column = f"Z_{tag_ent}TAGS" if tag_ent is not None else None
        candidates: list[tuple[str, set[str]]] = []
        # Core Data can create several *_TAGS tables; select only the Transaction–Tag link.
        for row in self._con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ):
            candidate = row["name"]
            match = (
                re.fullmatch(r"Z_(\d+)TAGS", candidate)
                if isinstance(candidate, str)
                else None
            )
            if match is None:
                continue
            columns = self._table_columns(candidate)
            if (
                candidate == table_name
                or int(match.group(1)) not in self._ent_to_typename
                or any(
                    re.fullmatch(r"Z_\d+TRANSACTIONS\d*", column) for column in columns
                )
            ):
                candidates.append((candidate, columns))

        if transaction_ent is None and tag_ent is None:
            storage = (
                RelationshipStorage.UNKNOWN
                if candidates
                else RelationshipStorage.ABSENT
            )
            return (
                storage,
                candidates[0][0] if len(candidates) == 1 else None,
                None,
                None,
            )
        if transaction_ent is None or tag_ent is None:
            return RelationshipStorage.UNKNOWN, None, None, None

        storage = (
            RelationshipStorage.PRESENT
            if candidates == [(table_name, {transaction_column, tag_column})]
            else RelationshipStorage.UNKNOWN
        )
        return storage, table_name, transaction_column, tag_column

    @staticmethod
    def _relationship_error(exc: Exception) -> LoadErrorKind:
        if isinstance(exc, KeyError):
            return LoadErrorKind.MISSING_FIELD
        if isinstance(exc, AssertionError):
            return LoadErrorKind.VALIDATION
        return LoadErrorKind.INVALID_VALUE

    def _skipped_relationship(
        self, record_id: ID | str | None, entity: str, exc: Exception
    ) -> SkippedRecord:
        return SkippedRecord(
            record_id=record_id,
            entity=entity,
            error=self._relationship_error(exc),
            exception_type=type(exc).__name__,
        )

    def query_objects(self, typenames: List[str]) -> List[Any]:
        """Query live rows against the verified cached entity mapping."""
        with self.read_transaction():
            return self._query_objects(typenames)

    def _query_objects(self, typenames: List[str]) -> List[Any]:
        ent_ids = [self._typename_to_ent.get(name) for name in typenames]
        ent_ids = [ent_id for ent_id in ent_ids if ent_id is not None]
        if not ent_ids:
            return []
        cur = self._con.cursor()
        res = cur.execute(
            """
        SELECT * FROM ZSYNCOBJECT WHERE Z_ENT in (%s)
        """
            % (",".join("?" * len(ent_ids))),
            ent_ids,
        )
        return res.fetchall()

    def close(self) -> None:
        """Close the read-only SQLite connection."""
        self._con.close()

    @contextmanager
    def _raw_read_transaction(self):
        """Provide snapshot ownership without consulting schema caches."""
        owns_transaction = not self._con.in_transaction
        if owns_transaction:
            self._con.execute("BEGIN")
        try:
            yield
        finally:
            if owns_transaction and self._con.in_transaction:
                self._con.rollback()

    def _require_active_read(self) -> None:
        if not self._con.in_transaction:
            raise DatabaseSchemaError(
                "database read transaction was interrupted; close and reopen the accessor"
            )

    def _verify_schema_identity(self) -> None:
        current = self._read_schema_identity()
        if current != self._schema_identity or (
            detect_schema_profile(self._con) != self._schema_profile
        ):
            raise DatabaseSchemaError(
                "database schema changed; close and reopen the accessor"
            )

    @contextmanager
    def read_transaction(self):
        """Keep cache-dependent reads on one verified SQLite snapshot."""
        if self._admission_depth:
            self._require_active_read()

        with self._raw_read_transaction():
            if not self._admission_depth:
                # Cached entity IDs and column profiles must still match the live schema.
                self._verify_schema_identity()
                self._require_active_read()
            self._admission_depth += 1
            try:
                yield
                self._require_active_read()
            finally:
                self._admission_depth -= 1

    def _construct_record(self, row, constructor: Callable):
        if isinstance(constructor, type) and issubclass(constructor, Record):
            model_constructor = cast(Callable[..., Any], constructor)
            return model_constructor(
                mapped_row(
                    row, cast(type, constructor), schema_profile=self.schema_profile
                )
            )
        raw_constructor = cast(Callable[..., Any], constructor)
        return raw_constructor(row)

    def get_record(self, pk_id: ID, constructor: Callable = Record):
        with self.read_transaction():
            cur = self._con.cursor()
            res = cur.execute(
                """
        SELECT * FROM ZSYNCOBJECT WHERE Z_PK = ?
        
        """,
                [pk_id],
            )

            return self._construct_record(res.fetchone(), constructor)

    def get_record_by_gid(self, gid: GID, constructor: Callable = Record):
        with self.read_transaction():
            cur = self._con.cursor()
            res = cur.execute(
                """
        SELECT * FROM ZSYNCOBJECT WHERE ZGID = ?
        
        """,
                [gid],
            )

            return self._construct_record(res.fetchone(), constructor)

    def read_category_assignments(
        self,
    ) -> tuple[Dict[ID, List[Tuple[ID, Decimal]]], RelationshipLoadReport]:
        with self.read_transaction():
            return self._read_category_assignments()

    def _read_category_assignments(
        self,
    ) -> tuple[Dict[ID, List[Tuple[ID, Decimal]]], RelationshipLoadReport]:
        transaction_map: Dict[ID, List[Tuple[ID, Decimal]]] = defaultdict(list)
        table_name = "ZCATEGORYASSIGMENT"
        columns = ("Z_PK", "ZCATEGORY", "ZTRANSACTION", "ZAMOUNT")
        storage = self._relationship_storage(
            entity_name="CategoryAssigment",
            table_name=table_name,
            required_columns=columns,
        )
        if storage != RelationshipStorage.PRESENT:
            return transaction_map, RelationshipLoadReport(
                storage=storage,
                storage_name=table_name,
            )

        skipped: list[SkippedRecord] = []
        rows = self._con.execute(
            f'SELECT {", ".join(columns)} FROM "{table_name}" '
            "WHERE ZTRANSACTION IS NOT NULL"
        ).fetchall()
        for row in rows:
            raw_source_id = row.get("Z_PK")
            source_id = raw_source_id if type(raw_source_id) is int else None
            try:
                require_integer_identity(raw_source_id)
                category_id = row["ZCATEGORY"]
                transaction_id = row["ZTRANSACTION"]
                require_integer_identity(category_id)
                require_integer_identity(transaction_id)
                amount = RDH.get_decimal(row["ZAMOUNT"])
                transaction_map[transaction_id].append((category_id, amount))
            except (AssertionError, KeyError, ValueError) as exc:
                skipped.append(
                    self._skipped_relationship(source_id, "CategoryAssigment", exc)
                )
                continue
        return transaction_map, RelationshipLoadReport(
            storage=storage,
            storage_name=table_name,
            source_count=len(rows),
            skipped=tuple(skipped),
        )

    def get_category_assignment(self) -> Dict[ID, List[Tuple[ID, Decimal]]]:
        """Return category assignments without completeness metadata."""
        return self.read_category_assignments()[0]

    def read_refund_maps(
        self,
    ) -> tuple[Dict[ID, ID], RelationshipLoadReport]:
        with self.read_transaction():
            return self._read_refund_maps()

    def _read_refund_maps(
        self,
    ) -> tuple[Dict[ID, ID], RelationshipLoadReport]:
        refund_to_withdraw: Dict[ID, ID] = {}
        table_name = "ZWITHDRAWREFUNDTRANSACTIONLINK"
        columns = ("Z_PK", "ZREFUNDTRANSACTION", "ZWITHDRAWTRANSACTION")
        storage = self._relationship_storage(
            entity_name="WithdrawRefundTransactionLink",
            table_name=table_name,
            required_columns=columns,
        )
        if storage != RelationshipStorage.PRESENT:
            return refund_to_withdraw, RelationshipLoadReport(
                storage=storage,
                storage_name=table_name,
            )

        skipped: list[SkippedRecord] = []
        rows = self._con.execute(
            f'SELECT {", ".join(columns)} FROM "{table_name}"'
        ).fetchall()
        for row in rows:
            raw_source_id = row.get("Z_PK")
            source_id = raw_source_id if type(raw_source_id) is int else None
            try:
                require_integer_identity(raw_source_id)
                refund_id = row["ZREFUNDTRANSACTION"]
                withdraw_id = row["ZWITHDRAWTRANSACTION"]
                require_integer_identity(refund_id)
                require_integer_identity(withdraw_id)
                if refund_id in refund_to_withdraw:
                    raise ValueError()
                refund_to_withdraw[refund_id] = withdraw_id
            except (AssertionError, KeyError, ValueError) as exc:
                skipped.append(
                    self._skipped_relationship(
                        source_id, "WithdrawRefundTransactionLink", exc
                    )
                )
                continue
        return refund_to_withdraw, RelationshipLoadReport(
            storage=storage,
            storage_name=table_name,
            source_count=len(rows),
            skipped=tuple(skipped),
        )

    def get_refund_maps(self) -> Dict[ID, ID]:
        """Return refund links without completeness metadata."""
        return self.read_refund_maps()[0]

    def read_tags_map(
        self,
    ) -> tuple[Dict[ID, List[ID]], RelationshipLoadReport]:
        with self.read_transaction():
            return self._read_tags_map()

    def _read_tags_map(
        self,
    ) -> tuple[Dict[ID, List[ID]], RelationshipLoadReport]:
        transactions_to_tags: Dict[ID, List[ID]] = defaultdict(list)
        storage, table_name, transaction_column, tag_column = (
            self._transaction_tag_storage()
        )
        if storage != RelationshipStorage.PRESENT:
            return transactions_to_tags, RelationshipLoadReport(
                storage=storage,
                storage_name=table_name,
            )
        columns = (cast(str, transaction_column), cast(str, tag_column))

        skipped: list[SkippedRecord] = []
        rows = self._con.execute(
            f'SELECT {", ".join(columns)} FROM "{table_name}"'
        ).fetchall()
        for position, row in enumerate(rows):
            transaction_id = row.get(transaction_column)
            tag_id = row.get(tag_column)
            try:
                require_integer_identity(transaction_id)
                require_integer_identity(tag_id)
                transactions_to_tags[transaction_id].append(tag_id)
            except (AssertionError, KeyError, ValueError) as exc:
                skipped.append(
                    self._skipped_relationship(f"row:{position}", "TransactionTag", exc)
                )
                continue
        return transactions_to_tags, RelationshipLoadReport(
            storage=storage,
            storage_name=table_name,
            source_count=len(rows),
            skipped=tuple(skipped),
        )

    def get_tags_map(self) -> Dict[ID, List[ID]]:
        """Return transaction tags without completeness metadata."""
        return self.read_tags_map()[0]

    def get_users(self) -> Dict[ID, str]:
        users_map: Dict[ID, str] = {}
        cur = self._con.cursor()
        res = cur.execute(
            """
        SELECT Z_PK, ZSYNCLOGIN FROM  "ZUSER"
        
        """
        )
        for row in res.fetchall():
            users_map[row["Z_PK"]] = row["ZSYNCLOGIN"]
        return users_map
