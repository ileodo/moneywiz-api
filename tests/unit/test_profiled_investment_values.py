from decimal import Decimal

import pytest

from moneywiz_api.managers.investment_holding_manager import InvestmentHoldingManager
from moneywiz_api.managers.transaction_manager import TransactionManager
from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.model.investment_holding import InvestmentHolding
from moneywiz_api.model.transaction import (
    InvestmentBuyTransaction,
    InvestmentSellTransaction,
)
from moneywiz_api.schema_profile import SchemaProfile


UNSUFFIXED_PROFILE = SchemaProfile(
    profile_id="unsuffixed-investment-columns",
    holding_number_of_shares_column="ZNUMBEROFSHARES",
    transaction_number_of_shares_column="ZNUMBEROFSHARES",
    price_per_share_column="ZPRICEPERSHARE",
)
MIXED_PROFILE = SchemaProfile(
    profile_id="mixed-investment-columns",
    holding_number_of_shares_column="ZNUMBEROFSHARES",
    transaction_number_of_shares_column="ZNUMBEROFSHARES1",
    price_per_share_column="ZPRICEPERSHARE1",
)
UNKNOWN_PROFILE = SchemaProfile("unknown", None, None, None)


def investment_transaction_row(ent: int, amount: float) -> dict:
    return {
        "Z_ENT": ent,
        "ZOBJECTCREATIONDATE": 0.0,
        "ZGID": f"investment-{ent}",
        "Z_PK": ent,
        "ZRECONCILED": 0,
        "ZAMOUNT1": amount,
        "ZDESC2": "Investment",
        "ZDATE1": 0.0,
        "ZNOTES1": None,
        "ZACCOUNT2": 1,
        "ZFEE2": 0.0,
        "ZINVESTMENTHOLDING": 2,
        "ZNUMBEROFSHARES": 2.0,
        "ZNUMBEROFSHARES1": 9.0,
        "ZPRICEPERSHARE": 10.0,
        "ZPRICEPERSHARE1": 1.0,
    }


def investment_holding_row() -> dict:
    return {
        "Z_ENT": 24,
        "ZOBJECTCREATIONDATE": 0.0,
        "ZGID": "holding",
        "Z_PK": 24,
        "ZINVESTMENTACCOUNT": 1,
        "ZOPENNINGNUMBEROFSHARES": None,
        "ZNUMBEROFSHARES": 2.0,
        "ZNUMBEROFSHARES1": 9.0,
        "ZSYMBOL": "ACME",
        "ZHOLDINGTYPE": None,
        "ZDESC": "Acme Corp.",
        "ZISPRICEPERSHAREAVAILABLEONLINE": 0,
        "ZINVESTMENTOBJECTTYPE": 0,
        "ZCOSTBASISOFMISSINGOBSHARES": 0.0,
    }


@pytest.mark.parametrize(
    ("constructor", "row"),
    [
        (InvestmentBuyTransaction, investment_transaction_row(40, -20.0)),
        (InvestmentSellTransaction, investment_transaction_row(41, 20.0)),
    ],
)
def test_transactions_use_selected_profile_alias(constructor, row) -> None:
    transaction = constructor(row, schema_profile=UNSUFFIXED_PROFILE)

    assert transaction.number_of_shares == Decimal("2.0")
    assert transaction.price_per_share == Decimal("10.0")


def test_holding_uses_selected_profile_alias() -> None:
    holding = InvestmentHolding(investment_holding_row(), UNSUFFIXED_PROFILE)

    assert holding.number_of_shares == Decimal("2.0")


@pytest.mark.parametrize(
    ("constructor", "transaction_row"),
    [
        (InvestmentBuyTransaction, investment_transaction_row(40, -9.0)),
        (InvestmentSellTransaction, investment_transaction_row(41, 9.0)),
    ],
)
def test_mixed_profile_uses_consumer_specific_share_aliases(
    constructor, transaction_row
) -> None:
    holding_row = investment_holding_row()

    transaction = constructor(transaction_row, MIXED_PROFILE)
    holding = InvestmentHolding(holding_row, MIXED_PROFILE)

    assert transaction.number_of_shares == Decimal("9.0")
    assert transaction.price_per_share == Decimal("1.0")
    assert holding.number_of_shares == Decimal("2.0")


class ProfileAccessor:
    schema_profile = UNSUFFIXED_PROFILE


def test_managers_pass_profile_to_investment_constructors() -> None:
    accessor = ProfileAccessor()
    transaction = TransactionManager().construct_record(
        InvestmentBuyTransaction, investment_transaction_row(40, -20.0), accessor
    )
    holding = InvestmentHoldingManager().construct_record(
        InvestmentHolding, investment_holding_row(), accessor
    )

    assert transaction.price_per_share == Decimal("10.0")
    assert holding.number_of_shares == Decimal("2.0")


class ManagerAccessor(ProfileAccessor):
    def __init__(self, typename: str, row: dict):
        self.typename = typename
        self.row = row

    def query_objects(self, _typenames):
        return [self.row]

    def typename_for(self, _ent_id):
        return self.typename

    def get_category_assignment(self):
        return {}

    def get_refund_maps(self):
        return {}

    def get_tags_map(self):
        return {}


def test_managers_load_profiled_investment_records() -> None:
    transaction_manager = TransactionManager()
    transaction_manager.load(
        ManagerAccessor(
            "InvestmentBuyTransaction", investment_transaction_row(40, -20.0)
        )
    )
    holding_manager = InvestmentHoldingManager()
    holding_manager.load(ManagerAccessor("InvestmentHolding", investment_holding_row()))

    assert transaction_manager.get(40).price_per_share == Decimal("10.0")
    assert holding_manager.get(24).number_of_shares == Decimal("2.0")


class StaticCursor:
    def __init__(self, row: dict):
        self.row = row

    def execute(self, _query, _parameters):
        return self

    def fetchone(self):
        return self.row


class StaticConnection:
    def __init__(self, row: dict):
        self.row = row

    def cursor(self):
        return StaticCursor(self.row)


def test_accessor_public_constructors_receive_schema_profile() -> None:
    transaction_accessor = DatabaseAccessor.__new__(DatabaseAccessor)
    transaction_accessor._con = StaticConnection(investment_transaction_row(40, -20.0))
    transaction_accessor._schema_profile = UNSUFFIXED_PROFILE
    holding_accessor = DatabaseAccessor.__new__(DatabaseAccessor)
    holding_accessor._con = StaticConnection(investment_holding_row())
    holding_accessor._schema_profile = UNSUFFIXED_PROFILE

    transaction = transaction_accessor.get_record(40, InvestmentBuyTransaction)
    holding = holding_accessor.get_record_by_gid("holding", InvestmentHolding)

    assert transaction.price_per_share == Decimal("10.0")
    assert holding.number_of_shares == Decimal("2.0")


@pytest.mark.parametrize(
    ("constructor", "row"),
    [
        (InvestmentBuyTransaction, investment_transaction_row(40, -20.0)),
        (InvestmentSellTransaction, investment_transaction_row(41, 20.0)),
        (InvestmentHolding, investment_holding_row()),
    ],
)
def test_investment_models_reject_ambiguous_profile(constructor, row) -> None:
    with pytest.raises(ValueError, match="unsupported investment schema profile"):
        constructor(row, UNKNOWN_PROFILE)
