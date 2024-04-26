import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Callable, Tuple
from decimal import Decimal

from moneywiz_api.model.record import Record
from moneywiz_api.model.raw_data_handler import RawDataHandler as RDH
from moneywiz_api.types import ENT_ID, ID, GID


class DatabaseAccessor:
    def __init__(self, db_path: Path):
        self._con = sqlite3.connect(db_path, uri=True)

        def dict_factory(cursor, row):
            record = {}
            for idx, col in enumerate(cursor.description):
                record[col[0]] = row[idx]
            return record

        self._con.row_factory = dict_factory

        self._ent_to_typename: Dict[ENT_ID, str] = self._load_primarykey()
        self._typename_to_ent: Dict[str, ENT_ID] = {
            v: k for k, v in self._ent_to_typename.items()
        }

    def _load_primarykey(self) -> Dict[int, str]:
        cur = self._con.cursor()
        res = cur.execute(
            """
        SELECT * FROM  "Z_PRIMARYKEY" ORDER BY "Z_ENT" LIMIT 1000 OFFSET 0;
        """
        )
        ent_to_typename: Dict[int, str] = {}
        for row in res.fetchall():
            ent_to_typename[row["Z_ENT"]] = row["Z_NAME"]
        return ent_to_typename

    def __repr__(self):
        return "\n".join(
            f"{key}: {value}" for key, value in self._ent_to_typename.items()
        )

    def typename_for(self, ent_id: ENT_ID) -> str:
        return self._ent_to_typename.get(ent_id)

    def ent_for(self, typename: str) -> ENT_ID:
        return self._typename_to_ent.get(typename)

    def query_objects(self, typenames: List[str]) -> List[Any]:
        cur = self._con.cursor()
        res = cur.execute(
            """
        SELECT * FROM ZSYNCOBJECT WHERE Z_ENT in (%s)
        """
            % (",".join("?" * len(typenames))),
            [self.ent_for(x) for x in typenames],
        )
        return res.fetchall()

    def get_record(self, pk_id: ID, constructor: Callable = Record):
        cur = self._con.cursor()
        res = cur.execute(
            """
        SELECT * FROM ZSYNCOBJECT WHERE Z_PK = ?
        
        """,
            [pk_id],
        )

        return constructor(res.fetchone())

    def get_record_by_gid(self, gid: GID, constructor: Callable = Record):
        cur = self._con.cursor()
        res = cur.execute(
            """
        SELECT * FROM ZSYNCOBJECT WHERE ZGID = ?
        
        """,
            [gid],
        )

        return constructor(res.fetchone())

    def get_category_assignment(self) -> Dict[ID, List[Tuple[ID, Decimal]]]:
        transaction_map: Dict[ID, List[Tuple[ID, Decimal]]] = defaultdict(list)
        cur = self._con.cursor()
        res = cur.execute(
            """
        SELECT ZCATEGORY, ZTRANSACTION, ZAMOUNT  FROM ZCATEGORYASSIGMENT WHERE ZTRANSACTION IS NOT NULL
        
        """
        )
        for row in res.fetchall():
            transaction_map[row["ZTRANSACTION"]].append(
                (row["ZCATEGORY"], RDH.get_decimal(row, "ZAMOUNT"))
            )
        return transaction_map

    def get_refund_maps(self) -> Dict[ID, ID]:
        refund_to_withdraw: Dict[ID, ID] = {}
        cur = self._con.cursor()
        res = cur.execute(
            """
        SELECT ZREFUNDTRANSACTION, ZWITHDRAWTRANSACTION  FROM ZWITHDRAWREFUNDTRANSACTIONLINK
        
        """
        )
        for row in res.fetchall():
            refund_to_withdraw[row["ZREFUNDTRANSACTION"]] = row["ZWITHDRAWTRANSACTION"]
        return refund_to_withdraw

    def get_tags_map(self) -> Dict[ID, List[ID]]:
        transactions_to_tags: Dict[ID, List[ID]] = defaultdict(list)
        cur = self._con.cursor()
        res = cur.execute(
            """
        SELECT Z_36TRANSACTIONS, Z_35TAGS FROM  Z_36TAGS
        
        """
        )
        for row in res.fetchall():
            transactions_to_tags[row["Z_36TRANSACTIONS"]].append(row["Z_35TAGS"])
        return transactions_to_tags

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
