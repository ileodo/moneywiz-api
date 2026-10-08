# MoneyWiz-API

![Static Badge](https://img.shields.io/badge/Python-3-blue?style=flat&logo=Python)
![PyPI](https://img.shields.io/pypi/v/moneywiz-api)

[![Buy Me A Coffee](https://cdn.buymeacoffee.com/buttons/v2/default-blue.png)](https://www.buymeacoffee.com/Ileodo)

A Python API to access MoneyWiz Sqlite database.

## Table of Contents

- [Get Started](#get-started)
- [Tests](#tests)
- [Contribution](#contribution)

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

### Schema profiles

`SchemaProfile` defines column aliases and converters for `Record` and its
subclasses. Build a profile directly from Python field specifications:

```python
from moneywiz_api import DEFAULT_SCHEMA_PROFILE, MoneywizApi, SchemaProfile
from moneywiz_api.model.tag import Tag
from moneywiz_api.model.schema_fields import schema_field

column_map = {
    **DEFAULT_SCHEMA_PROFILE.column_map,
    Tag: {
        **DEFAULT_SCHEMA_PROFILE.column_map[Tag.__name__],
        "name": schema_field("CUSTOM_TAG_NAME", "ZNAME6"),
    },
}
profile = SchemaProfile(column_map)
profile.validate()
api = MoneywizApi("<path_to_your_sqlite_file>", schema_profile=profile)
```

Use `schema_field`, `datetime_field`, `decimal_field`,
`nullable_decimal_field`, or `is_one_field` to define each field. Base-class
fields are inherited by subclasses. `profile.validate()` checks public dataclass
fields on loaded `Record` subclasses and reports any missing definitions.

`SchemaProfile.get_field(row, model_class, field_name)` resolves a field from a
raw row. Record constructors use the profile to assign public fields; private
fields and model-specific fixups stay in the constructors. Pass a profile to a manager or directly to a model constructor to use a custom mapping.

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
