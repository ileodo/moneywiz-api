# MoneyWiz-API

![Static Badge](https://img.shields.io/badge/Python-3-blue?style=flat&logo=Python)
![PyPI](https://img.shields.io/pypi/v/moneywiz-api)

<a href="https://www.buymeacoffee.com/Ileodo" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-blue.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>

A Python API to access MoneyWiz Sqlite database.

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

## Contribution

This project is in very early stage, all contributions are welcomed!
