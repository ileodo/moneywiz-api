"""Field definitions for each model in a MoneyWiz database schema."""

from dataclasses import fields as dataclass_fields
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Iterable, Mapping

if TYPE_CHECKING:
    from moneywiz_api.model.record import Record

from moneywiz_api.model.schema_fields import (
    FieldSpec,
    datetime_field,
    decimal_field,
    is_one_field,
    nullable_decimal_field,
    schema_field,
)
from moneywiz_api.utils import get_datetime

ColumnMap = (
    Mapping[str, Mapping[str, FieldSpec]]
    | Mapping[type, Mapping[str, FieldSpec]]
    | Mapping[str | type, Mapping[str, FieldSpec]]
)


class SchemaProfile:
    """A per-model schema, resolved in base-to-subclass inheritance order.

    ``column_map`` keys may be model classes or their names. Each entry defines that class's
    own fields; inherited fields are supplied by the entries for its bases.
    """

    def __init__(self, column_map: ColumnMap):
        self.column_map = MappingProxyType(
            {
                key if isinstance(key, str) else key.__name__: MappingProxyType(
                    dict(value)
                )
                for key, value in column_map.items()
            }
        )

    def get_field(
        self, row: Mapping[str, Any], model_cls: type, field_name: str
    ) -> Any:
        """Resolve one model field directly from a raw database row."""
        spec = self.fields_for(model_cls)[field_name]
        for alias in spec.aliases:
            if alias in row:
                value = row[alias]
                if spec.converter is not None:
                    try:
                        return spec.converter(value)
                    except Exception as error:
                        from moneywiz_api.model.raw_data_handler import RawDataHandler

                        raise RuntimeError(
                            f"Failed to convert field {field_name} using column {alias} "
                            f"with value {value}, the exception was: {error}. "
                            f"the row was: {RawDataHandler.filter_row(dict(row))}"
                        ) from error
                return value
        raise KeyError(
            f"Could not resolve field {field_name}. Tried {list(spec.aliases)}. "
            f"Available columns: {list(row.keys())}"
        )

    def assign_fields(self, record: "Record", row: Mapping[str, Any]) -> None:
        """Assign every public dataclass field directly from a raw row."""
        for field in dataclass_fields(record):
            if not field.name.startswith("_"):
                setattr(
                    record, field.name, self.get_field(row, type(record), field.name)
                )

    def fields_for(self, model_cls: type) -> dict[str, FieldSpec]:
        fields: dict[str, FieldSpec] = {}
        for cls in reversed(model_cls.mro()):
            # Preserve support for application-defined Record subclasses.
            fields.update(cls.__dict__.get("FIELDS", {}))
            fields.update(self.column_map.get(cls.__name__, {}))
        return fields

    def validate(self, model_classes: Iterable[type["Record"]] | None = None) -> None:
        """Raise ValueError for public dataclass fields without definitions.

        By default, check Record and all currently loaded subclasses. An explicit
        iterable can restrict validation to selected models. Inherited definitions
        count, and fields whose names begin with an underscore are ignored.
        """
        from moneywiz_api.model.record import Record

        if model_classes is None:
            discovered = {Record}
            pending = [Record]
            while pending:
                for subclass in pending.pop().__subclasses__():
                    if subclass not in discovered:
                        discovered.add(subclass)
                        pending.append(subclass)
            model_classes = sorted(discovered, key=lambda cls: cls.__name__)

        missing: list[str] = []
        for model_cls in model_classes:
            definitions = self.fields_for(model_cls)
            missing.extend(
                f"{model_cls.__name__}.{field.name}"
                for field in dataclass_fields(model_cls)
                if not field.name.startswith("_") and field.name not in definitions
            )
        if missing:
            raise ValueError("Missing schema field definitions: " + ", ".join(missing))


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
