from os.path import expanduser
from pathlib import Path
from code import interact
from typing import Dict, List

import click
import logging

from moneywiz_api.cli.helpers import ShellHelper
from moneywiz_api.moneywiz_api import MoneywizApi


def get_default_path() -> Path:
    return Path(
        expanduser(
            "~/Library/Containers/com.moneywiz.personalfinance/Data/Documents/.AppData/ipadMoneyWiz.sqlite"
        )
    )


@click.command()
@click.argument(
    "DB_FILE_PATH",
    type=click.Path(writable=False, readable=True, exists=True),
    default=get_default_path(),
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
)
def main(db_file_path, log_level):
    """
    Interactive shell to access MoneyWiz (Read-only)
    """

    # Configure logging level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")

    logging.basicConfig(level=numeric_level)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    moneywiz_api = MoneywizApi(db_file_path)

    (
        accessor,
        account_manager,
        payee_manager,
        category_manager,
        transaction_manager,
        investment_holding_manager,
    ) = (
        moneywiz_api.accessor,
        moneywiz_api.account_manager,
        moneywiz_api.payee_manager,
        moneywiz_api.category_manager,
        moneywiz_api.transaction_manager,
        moneywiz_api.investment_holding_manager,
    )

    helper = ShellHelper(moneywiz_api)

    names: Dict[str, str] = {
        f"{moneywiz_api=}".split("=")[0]: "MoneyWiz API",
        f"{accessor=}".split("=")[0]: "MoneyWiz Database Accessor",
        f"{account_manager=}".split("=")[0]: "Account Manager",
        f"{payee_manager=}".split("=")[0]: "Payee Manager",
        f"{category_manager=}".split("=")[0]: "Category Manageer",
        f"{transaction_manager=}".split("=")[0]: "Transaction Manager",
        f"{investment_holding_manager=}".split("=")[0]: "Investment Holding Manager",
        f"{helper=}".split("=")[0]: "Shell Helper",
    }

    banner: List[str] = (
        f"Read-only MoneyWiz Shell on {db_file_path}",
        "",
        "Avaliable components:",
        *[f"- {component:30}  {desc}" for component, desc in names.items()],
        "===================================================================",
    )

    interact(local=locals(), banner="\n".join(banner))


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
