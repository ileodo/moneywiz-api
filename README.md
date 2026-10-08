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

`MoneywizApi` resolves the default `SchemaProfile` from the database path when it
is constructed, then validates the profile before loading records. You do not
need to pass a profile to `MoneywizApi`:

```python
from moneywiz_api import MoneywizApi

api = MoneywizApi("<path_to_your_sqlite_file>")
```

A `SchemaProfile` maps each `Record` field to one or more database column names
and optional converters. Field specifications are available from
`moneywiz_api.schema.schema_fields`, including `schema_field`,
`datetime_field`, `decimal_field`, `nullable_decimal_field`, and `is_one_field`.
Definitions for base classes are inherited by their subclasses. Calling
`profile.validate()` checks that every public dataclass field on loaded `Record`
subclasses has a definition; fields whose names start with `_` are ignored.

To create a customized profile, start with `DEFAULT_SCHEMA_PROFILE` and replace
the field mapping you need:

```python
from moneywiz_api import DEFAULT_SCHEMA_PROFILE, SchemaProfile
from moneywiz_api.model.tag import Tag
from moneywiz_api.schema.schema_fields import schema_field

column_map = {
    **DEFAULT_SCHEMA_PROFILE.column_map,
    Tag: {
        **DEFAULT_SCHEMA_PROFILE.column_map[Tag.__name__],
        "name": schema_field("CUSTOM_TAG_NAME", "ZNAME6"),
    },
}
profile = SchemaProfile(column_map)
profile.validate()
```

`SchemaProfileResolver(db_path, baseline=None).resolve()` enriches a profile
with database-specific tag-join table details. When no baseline is provided, it
uses `DEFAULT_SCHEMA_PROFILE`. The resolved profile can be passed to `MoneywizApi` or the lower-level
`DatabaseAccessor`:

```python
db_path = "<path_to_your_sqlite_file>"
resolved_profile = SchemaProfileResolver(db_path, profile).resolve()
api = MoneywizApi(db_path, schema_profile=resolved_profile)
```

`SchemaProfile.create_record(row, ModelClass)` resolves all public fields from
a raw row, reports field-resolution failures together, and creates the model
instance. Record
classes receive mapped field values and do not depend on `SchemaProfile`.

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
