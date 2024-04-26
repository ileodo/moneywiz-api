from dataclasses import asdict
from typing import Dict
from pathlib import Path

import logging
import json
import click
import pandas as pd

from moneywiz_api import MoneywizApi
from moneywiz_api.managers.record_manager import RecordManager
from moneywiz_api.types import ID, GID


logger = logging.getLogger(__name__)


class ShellHelper:

    def __init__(self, moneywiz_api: MoneywizApi) -> None:
        self._mw_api = moneywiz_api

    def view_id(self, record_id: ID):
        record = self._mw_api.accessor.get_record(record_id)
        click.echo(self._mw_api.accessor.typename_for(record.ent()))
        click.echo(json.dumps(record.filtered(), sort_keys=True, indent=4))

    def view_gid(self, record_gid: GID):
        record = self._mw_api.accessor.get_record_by_gid(record_gid)
        click.echo(self._mw_api.accessor.typename_for(record.ent()))
        click.echo(json.dumps(record.filtered(), sort_keys=True, indent=4))

    def write_stats_data_files(self, path_prefix: Path = Path("data/stats")):
        Path(path_prefix).mkdir(parents=True, exist_ok=True)
        managers_map: Dict[str, object] = {
            "ent": self._mw_api.accessor,
            "account": self._mw_api.account_manager,
            "payee": self._mw_api.payee_manager,
            "category": self._mw_api.category_manager,
            "transaction": self._mw_api.transaction_manager,
            "investment_holding": self._mw_api.investment_holding_manager,
        }

        for name, obj in managers_map.items():
            with open(f"{path_prefix}/{name}.data", "w", encoding="utf-8") as file:
                click.echo(obj, file=file)

    def pd_table(self, manager: RecordManager) -> pd.DataFrame:
        records = manager.records().values()
        df = pd.DataFrame.from_records([r.as_dict() for r in records])
        return df

    def users_table(self) -> pd.DataFrame:
        users = self._mw_api.accessor.get_users()
        records = [
            {"id": id, "login_name": login_name} for id, login_name in users.items()
        ]
        return pd.DataFrame.from_records(records).sort_values(by=["id"], ascending=True)

    def categories_table(self, user_id: ID) -> pd.DataFrame:
        categories = self._mw_api.category_manager.get_categories_for_user(user_id)
        return pd.DataFrame.from_records(
            [category.as_dict() for category in categories]
        ).sort_values(by=["id"], ascending=True)

    def accounts_table(self, user_id: ID) -> pd.DataFrame:
        # pd.set_option("display.max_colwidth", None)
        # pd.set_option("display.max_rows", None)

        accounts = self._mw_api.account_manager.get_accounts_for_user(user_id)
        return pd.DataFrame.from_records(
            [account.as_dict() for account in accounts]
        ).sort_values(by=["group_id", "display_order"])

    def investment_holdings_table(self, account_id: ID) -> pd.DataFrame:
        investment_holdings = (
            self._mw_api.investment_holding_manager.get_holdings_for_account(account_id)
        )
        return pd.DataFrame.from_records(
            [investment_holding.as_dict() for investment_holding in investment_holdings]
        ).sort_values(by=["account", "symbol"])

    def transactions_table(self, account_id: ID) -> pd.DataFrame:
        records = self._mw_api.transaction_manager.get_all_for_account(account_id)

        return pd.DataFrame.from_records(
            [record.as_dict() for record in records]
        ).sort_values(by=["datetime"], ascending=False)
