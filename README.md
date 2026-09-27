# MoneyWiz-API

![Static Badge](https://img.shields.io/badge/Python-3-blue?style=flat&logo=Python)
![PyPI](https://img.shields.io/pypi/v/moneywiz-api)

[![Buy Me A Coffee](https://cdn.buymeacoffee.com/buttons/v2/default-blue.png)](https://www.buymeacoffee.com/Ileodo)

A Python API to access MoneyWiz Sqlite database.

## Table of Contents

- [Get Started](#get-started)
- [Tests](#tests)
- [Contribution](#contribution)
- [Read completeness](#read-completeness)

## Get Started

```bash
pip install moneywiz-api
```

```python
from moneywiz_api import MoneywizApi

moneywizApi = MoneywizApi("<path_to_your_sqlite_file>")

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

record = accessor.get_record(record_id)
print(record)
```

It also offers a interactive shell `moneywiz-cli`.

## Tests

Run unit tests without a database:

```bash
uv run pytest tests/unit
```

Integration tests are opt-in and never read a CLI default database path. Point
`MONEYWIZ_TEST_DB_PATH` at a disposable MoneyWiz SQLite test database:

```bash
MONEYWIZ_TEST_DB_PATH=/absolute/path/to/test.sqlite uv run pytest tests
```

## Contribution

This project is in very early stage, all contributions are welcomed!

## Read completeness

```python
from contextlib import closing
from pathlib import Path

from moneywiz_api import MoneywizApi

with closing(MoneywizApi(Path("moneywiz.sqlite"), managers=("accounts",))) as api:
    report = api.completeness()
    if not report.complete:
        raise RuntimeError("incomplete read")
    accounts = api.account_manager.records()
```

By default, all managers load. Select from `accounts`, `payees`, `categories`,
`transactions`, `investment_holdings`, and `tags`. `load(managers=...)` refreshes
the selection and previously loaded managers in one read transaction. A failed
reload invalidates those managers. Reports contain source and parsed IDs,
identity-only skipped row diagnostics, and transaction relationship status.
Unknown layouts prevent a complete result. Reopen the read-only API after a
schema change.
