"""Resolve database-specific metadata for a schema profile."""

import re
import sqlite3
from pathlib import Path

from moneywiz_api.model.investment_holding import InvestmentHolding
from moneywiz_api.model.transaction import (
    InvestmentBuyTransaction,
    InvestmentSellTransaction,
)

from moneywiz_api.schema.schema_fields import (
    FieldSpec,
    datetime_field,
    decimal_field,
    is_one_field,
    nullable_decimal_field,
    schema_field,
)
from moneywiz_api.schema.schema_profile import SchemaProfile, TagTableInfo
from moneywiz_api.utils import get_datetime


class UnsupportedInvestmentSchemaError(ValueError):
    """Raised when investment columns cannot be selected safely for a store."""


class SchemaProfileResolver:
    """Build a profile from a database path and an optional baseline profile."""

    def __init__(self, db_path: str | Path, baseline: SchemaProfile | None = None):
        self._db_path = db_path
        self._baseline = DEFAULT_SCHEMA_PROFILE if baseline is None else baseline

    def resolve(self) -> SchemaProfile:
        """Return the baseline enriched with database-specific schema details."""
        connection = sqlite3.connect(self._db_path, uri=True)
        connection.row_factory = sqlite3.Row
        try:
            column_map = {
                model_name: dict(fields)
                for model_name, fields in self._baseline.column_map.items()
            }
            self._resolve_investment_fields(connection, column_map)
            return SchemaProfile(column_map).with_tag_table_info(
                self._baseline.tag_table_info or self._get_tags_table_info(connection)
            )
        finally:
            connection.close()

    def _resolve_investment_fields(
        self,
        connection: sqlite3.Connection,
        column_map: dict[str | type, dict[str, FieldSpec]],
    ) -> None:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if "ZSYNCOBJECT" not in tables or "Z_PRIMARYKEY" not in tables:
            return

        entities: dict[str, int] = {
            row["Z_NAME"]: row["Z_ENT"]
            for row in connection.execute(
                "SELECT Z_ENT, Z_NAME FROM Z_PRIMARYKEY WHERE Z_NAME IN (?, ?, ?)",
                (
                    "InvestmentHolding",
                    "InvestmentBuyTransaction",
                    "InvestmentSellTransaction",
                ),
            ).fetchall()
        }
        if not entities:
            return

        active_entity_ids = {
            row["Z_ENT"]
            for row in connection.execute(
                "SELECT DISTINCT Z_ENT FROM ZSYNCOBJECT WHERE Z_ENT IN ("
                + ", ".join("?" for _ in entities)
                + ")",
                tuple(entities.values()),
            ).fetchall()
        }
        active_entities = {
            name: entity_id
            for name, entity_id in entities.items()
            if entity_id in active_entity_ids
        }
        if not active_entities:
            return

        columns = {
            row["name"]
            for row in connection.execute('PRAGMA table_info("ZSYNCOBJECT")')
        }
        for models, field_name, aliases in (
            (
                (InvestmentHolding,),
                "number_of_shares",
                ("ZNUMBEROFSHARES", "ZNUMBEROFSHARES1"),
            ),
            (
                (InvestmentBuyTransaction, InvestmentSellTransaction),
                "number_of_shares",
                ("ZNUMBEROFSHARES", "ZNUMBEROFSHARES1"),
            ),
            (
                (InvestmentBuyTransaction, InvestmentSellTransaction),
                "price_per_share",
                ("ZPRICEPERSHARE", "ZPRICEPERSHARE1"),
            ),
        ):
            specs = {
                model: self._baseline.specs_for(model)[field_name]
                for model in models
                if model.__name__ in active_entities
            }
            automatic_specs = {
                model: spec
                for model, spec in specs.items()
                if spec.aliases
                == DEFAULT_SCHEMA_PROFILE.specs_for(model)[field_name].aliases
            }
            if not automatic_specs:
                continue
            column = self._column_for_entities(
                connection,
                columns,
                aliases[0],
                aliases[1],
                tuple(active_entities[model.__name__] for model in automatic_specs),
            )
            if column is None:
                consumer = (
                    "holding shares column"
                    if models[0] is InvestmentHolding
                    else "transaction columns"
                )
                raise UnsupportedInvestmentSchemaError(
                    f"unsupported investment schema profile: ambiguous {consumer}"
                )
            for model, spec in automatic_specs.items():
                column_map.setdefault(model.__name__, {})[field_name] = FieldSpec(
                    (column,), spec.converter
                )

    @staticmethod
    def _column_for_entities(
        connection: sqlite3.Connection,
        columns: set[str],
        unsuffixed: str,
        suffixed: str,
        entity_ids: tuple[int, ...],
    ) -> str | None:
        has_unsuffixed = unsuffixed in columns
        has_suffixed = suffixed in columns
        if has_unsuffixed != has_suffixed:
            return unsuffixed if has_unsuffixed else suffixed
        if not has_unsuffixed:
            return None

        placeholders = ", ".join("?" for _ in entity_ids)
        counts = connection.execute(
            f'SELECT COUNT("{unsuffixed}"), COUNT("{suffixed}") '
            f'FROM "ZSYNCOBJECT" WHERE "Z_ENT" IN ({placeholders})',
            entity_ids,
        ).fetchone()
        unsuffixed_count, suffixed_count = counts[0], counts[1]
        if unsuffixed_count and not suffixed_count:
            return unsuffixed
        if suffixed_count and not unsuffixed_count:
            return suffixed
        return None

    @staticmethod
    def _get_tags_table_info(connection: sqlite3.Connection) -> TagTableInfo:
        cursor = connection.cursor()
        result = cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        tag_tables = []
        for row in result.fetchall():
            match = re.fullmatch(r"Z_(\d+)TAGS", row["name"])
            if match:
                tag_tables.append((int(match.group(1)), row["name"]))

        if not tag_tables:
            raise ValueError("Could not find a tags join table matching Z_<number>TAGS")

        table_name = max(tag_tables)[1]
        result = cursor.execute(f'PRAGMA table_info("{table_name}")')
        columns = [row["name"] for row in result.fetchall()]
        transaction_columns = [
            column for column in columns if re.fullmatch(r"Z_\d+TRANSACTIONS", column)
        ]
        tag_columns = [
            column for column in columns if re.fullmatch(r"Z_\d+TAGS", column)
        ]

        if len(transaction_columns) != 1 or len(tag_columns) != 1:
            raise ValueError(f"Could not find expected tag columns in {table_name}")

        return TagTableInfo(table_name, transaction_columns[0], tag_columns[0])


DEFAULT_SCHEMA_PROFILE = SchemaProfile(
    {
        "Record": {
            "ent": schema_field("Z_ENT"),
            "created_at": datetime_field(
                "ZOBJECTCREATIONDATE", value_if_null=get_datetime(0.0)
            ),
            "gid": schema_field("ZGID"),
            "id": schema_field("Z_PK"),
        },
        "Account": {
            "display_order": schema_field("ZDISPLAYORDER"),
            "group_id": schema_field("ZGROUPID"),
            "name": schema_field("ZNAME"),
            "currency": schema_field("ZCURRENCYNAME"),
            "opening_balance": decimal_field("ZOPENINGBALANCE"),
            "info": schema_field("ZINFO"),
            "user": schema_field("ZUSER"),
        },
        "BankChequeAccount": {},
        "BankSavingAccount": {},
        "CashAccount": {},
        "CreditCardAccount": {
            "statement_day": schema_field("ZSTATEMENTENDDAY"),
        },
        "LoanAccount": {},
        "InvestmentAccount": {},
        "ForexAccount": {},
        "Category": {
            "name": schema_field("ZNAME2"),
            "parent_id": schema_field("ZPARENTCATEGORY"),
            "type": schema_field("ZTYPE2"),
            "user": schema_field("ZUSER3"),
        },
        "Payee": {
            "name": schema_field("ZNAME5"),
            "user": schema_field("ZUSER7"),
        },
        "Tag": {
            "name": schema_field("ZNAME6"),
            "user": schema_field("ZUSER8"),
        },
        "InvestmentHolding": {
            "account": schema_field("ZINVESTMENTACCOUNT"),
            "opening_number_of_shares": nullable_decimal_field(
                "ZOPENNINGNUMBEROFSHARES"
            ),
            "number_of_shares": nullable_decimal_field("ZNUMBEROFSHARES"),
            "symbol": schema_field("ZSYMBOL"),
            "holding_type": schema_field("ZHOLDINGTYPE"),
            "description": schema_field("ZDESC"),
            "price_per_share_available_online": is_one_field(
                "ZISPRICEPERSHAREAVAILABLEONLINE"
            ),
        },
        "Transaction": {
            "reconciled": is_one_field("ZRECONCILED"),
            "amount": decimal_field("ZAMOUNT1"),
            "description": schema_field("ZDESC2"),
            "datetime": datetime_field("ZDATE1"),
            "notes": schema_field("ZNOTES1"),
        },
        "DepositTransaction": {
            "account": schema_field("ZACCOUNT2"),
            "payee": schema_field("ZPAYEE2"),
            "original_currency": schema_field("ZORIGINALCURRENCY"),
            "original_amount": decimal_field("ZORIGINALAMOUNT"),
            "original_exchange_rate": nullable_decimal_field("ZORIGINALEXCHANGERATE"),
        },
        "InvestmentExchangeTransaction": {
            "account": schema_field("ZACCOUNT2"),
            "from_investment_holding": schema_field("ZFROMINVESTMENTHOLDING"),
            "from_symbol": schema_field("ZFROMSYMBOL"),
            "to_investment_holding": schema_field("ZTOINVESTMENTHOLDING"),
            "to_symbol": schema_field("ZTOSYMBOL"),
            "from_number_of_shares": schema_field("ZFROMNUMBEROFSHARES"),
            "to_number_of_shares": schema_field("ZTONUMBEROFSHARES"),
            "original_fee": schema_field("ZORIGINALFEE"),
            "original_fee_currency": schema_field("ZORIGINALFEECURRENCY"),
        },
        "InvestmentTransaction": {},
        "InvestmentBuyTransaction": {
            "account": schema_field("ZACCOUNT2"),
            "fee": decimal_field("ZFEE2"),
            "investment_holding": schema_field("ZINVESTMENTHOLDING"),
            "number_of_shares": decimal_field("ZNUMBEROFSHARES"),
            "price_per_share": decimal_field("ZPRICEPERSHARE1"),
        },
        "InvestmentSellTransaction": {
            "account": schema_field("ZACCOUNT2"),
            "fee": decimal_field("ZFEE2"),
            "investment_holding": schema_field("ZINVESTMENTHOLDING"),
            "number_of_shares": decimal_field("ZNUMBEROFSHARES"),
            "price_per_share": decimal_field("ZPRICEPERSHARE1"),
        },
        "ReconcileTransaction": {
            "account": schema_field("ZACCOUNT2"),
            "reconcile_amount": nullable_decimal_field("ZRECONCILEAMOUNT"),
            "reconcile_number_of_shares": nullable_decimal_field(
                "ZRECONCILENUMBEROFSHARES"
            ),
        },
        "RefundTransaction": {
            "account": schema_field("ZACCOUNT2"),
            "payee": schema_field("ZPAYEE2"),
            "original_currency": schema_field("ZORIGINALCURRENCY"),
            "original_amount": decimal_field("ZORIGINALAMOUNT"),
            "original_exchange_rate": nullable_decimal_field("ZORIGINALEXCHANGERATE"),
        },
        "TransferBudgetTransaction": {},
        "TransferDepositTransaction": {
            "account": schema_field("ZACCOUNT2"),
            "sender_account": schema_field("ZSENDERACCOUNT"),
            "sender_transaction": schema_field("ZSENDERTRANSACTION"),
            "original_amount": decimal_field("ZORIGINALAMOUNT"),
            "original_currency": schema_field("ZORIGINALCURRENCY"),
            "sender_amount": decimal_field("ZORIGINALSENDERAMOUNT"),
            "sender_currency": schema_field("ZORIGINALSENDERCURRENCY"),
            "original_fee": nullable_decimal_field("ZORIGINALFEE"),
            "original_fee_currency": schema_field("ZORIGINALFEECURRENCY"),
            "original_exchange_rate": decimal_field("ZORIGINALEXCHANGERATE"),
        },
        "TransferWithdrawTransaction": {
            "account": schema_field("ZACCOUNT2"),
            "recipient_account": schema_field("ZRECIPIENTACCOUNT1"),
            "recipient_transaction": schema_field("ZRECIPIENTTRANSACTION"),
            "original_amount": decimal_field("ZORIGINALAMOUNT"),
            "original_currency": schema_field("ZORIGINALCURRENCY"),
            "recipient_amount": nullable_decimal_field("ZORIGINALRECIPIENTAMOUNT"),
            "recipient_currency": schema_field("ZORIGINALRECIPIENTCURRENCY"),
            "original_fee": nullable_decimal_field("ZORIGINALFEE"),
            "original_fee_currency": schema_field("ZORIGINALFEECURRENCY"),
            "original_exchange_rate": decimal_field("ZORIGINALEXCHANGERATE"),
        },
        "WithdrawTransaction": {
            "account": schema_field("ZACCOUNT2"),
            "payee": schema_field("ZPAYEE2"),
            "original_currency": schema_field("ZORIGINALCURRENCY"),
            "original_amount": decimal_field("ZORIGINALAMOUNT"),
            "original_exchange_rate": nullable_decimal_field("ZORIGINALEXCHANGERATE"),
        },
    }
)
