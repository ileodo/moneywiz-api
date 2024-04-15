import logging
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Callable, Tuple

from moneywiz_api.model.record import Record
from moneywiz_api.types import ENT_ID, ID


logger = logging.getLogger(__name__)


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
        logger.debug("Entities found in the Database:")
        for row in res.fetchall():
            logger.debug(f"({row['Z_ENT']}) {row['Z_NAME']}")
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

    def get_category_assignment(self) -> Dict[ID, List[Tuple[ID, float]]]:
        transaction_map: Dict[ID, List[Tuple[ID, float]]] = defaultdict(list)
        cur = self._con.cursor()
        res = cur.execute(
            """
        SELECT ZCATEGORY, ZTRANSACTION, ZAMOUNT  FROM ZCATEGORYASSIGMENT WHERE ZTRANSACTION IS NOT NULL

        """
        )
        for row in res.fetchall():
            transaction_map[row["ZTRANSACTION"]].append(
                (row["ZCATEGORY"], row["ZAMOUNT"])
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

    def find_tags_map(self) -> Tuple[str, str, str]:
        cur0 = self._con.cursor()
        res0 = cur0.execute(
            """
        SELECT name FROM sqlite_master WHERE type='table' AND name like 'Z_%TAGS'

        """
        )
        for row0 in res0.fetchall():
            cur1 = self._con.cursor()
            res1 = cur1.execute("PRAGMA table_info({})".format(row0["name"]))
            tag_map_score = 0
            tag_transactions_key = None
            tag_tags_key = None
            for row1 in res1.fetchall():
                if re.match(r"^Z_[0-9]{2}TRANSACTIONS$", row1["name"]):
                    tag_map_score += 1
                    tag_transactions_key = row1["name"]
                elif re.match(r"^Z_[0-9]{2}TAGS$", row1["name"]):
                    tag_map_score += 1
                    tag_tags_key = row1["name"]

            if tag_map_score == 2:
                return row0["name"], tag_transactions_key, tag_tags_key

        return None, None, None

    def get_tags_map(self) -> Dict[ID, List[ID]]:
        tags_table, transaction_col, tags_col = self.find_tags_map()
        transactions_to_tags: Dict[ID, List[ID]] = defaultdict(list)
        cur = self._con.cursor()
        res = cur.execute(
            "SELECT {}, {} FROM {}".format(transaction_col, tags_col, tags_table)
        )

        for row in res.fetchall():
            transactions_to_tags[row[transaction_col]].append(row[tags_col])
        return transactions_to_tags
