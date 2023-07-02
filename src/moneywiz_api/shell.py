import pathlib
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Dict
import logging
import json
import code
import pandas as pd

from moneywiz_api import MoneywizApi
from moneywiz_api.types import ID

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)

DB_PATH = sys.argv[1]

moneywizApi = MoneywizApi(Path(DB_PATH))

(
    accessor,
    account_manager,
    payee_manager,
    category_manager,
    transaction_manager,
    investment_holding_manager,
) = (
    moneywizApi.accessor,
    moneywizApi.account_manager,
    moneywizApi.payee_manager,
    moneywizApi.category_manager,
    moneywizApi.transaction_manager,
    moneywizApi.investment_holding_manager,
)


def view(record_id: ID):
    record = accessor.get_record(record_id)
    print(accessor.typename_for(record.ent()))
    print(json.dumps(record.filtered(), sort_keys=True, indent=4))


def print_investment_holdings_for_account(account_id: ID):
    for x in [
        f"{h.id}: 0, #{h.symbol}"
        for h in investment_holding_manager.get_holdings_for_account(account_id)
    ]:
        print(x)


def write_state_data_files():
    path_prefix = "data/state"
    pathlib.Path(path_prefix).mkdir(parents=True, exist_ok=True)
    managers_map: Dict[str, object] = {
        "ent": accessor,
        "account": account_manager,
        "payee": payee_manager,
        "category": category_manager,
        "transaction": transaction_manager,
        "investment_holding": investment_holding_manager,
    }

    for name, obj in managers_map.items():
        with open(f"{path_prefix}/{name}.data", "w") as file:
            print(obj, file=file)


def account_tables(user_id: ID):
    pd.set_option("display.max_colwidth", None)
    pd.set_option("display.max_rows", None)

    accounts = account_manager.get_accounts_for_user(user_id)

    df = pd.DataFrame.from_records([asdict(account) for account in accounts])
    print(
        df.sort_values(by=["_group_id", "_display_order"])[["id", "name"]].to_string(
            index=False
        )
    )


def transactions_for_account(account_id: ID):
    records = transaction_manager.get_all_for_account(account_id)

    df = pd.DataFrame.from_records([asdict(record) for record in records])
    print(
        df.sort_values(by=["date"], ascending=False)[
            ["id", "date", "amount"]
        ].to_string(index=False)
    )

    print("total_amount:", df["amount"].sum())
    print("number of transactions:", df.shape[0])


def generate_categories_list(user_id: ID):
    categories = category_manager.get_categories_for_user(user_id)

    for category in categories:
        print(
            f"""{category.id}: ["{category.type}", {", ".join(['"'+ x.replace(" ","") + '"' for x in category_manager.get_name_chain(category.id)])}],"""
        )


if __name__ == "__main__":
    print("Shell on:" + DB_PATH)
    code.interact(local=locals())
