# Repository Guidelines

## Project Structure & Module Organization

This is a Python 3.10+ package for reading MoneyWiz SQLite databases. Source lives in `src/moneywiz_api/`: `schema/` maps database columns and converts values, `model/` defines records, `database_accessor.py` runs queries, `managers/` organize loaded records, and `cli/` implements `moneywiz-cli`. Put database-free tests in `tests/unit/` and tests requiring a MoneyWiz database in `tests/integration/`. Packaging and tool settings are in `pyproject.toml`; CI is in `.github/workflows/`.

## Build, Test, and Development Commands

Create a local environment with `python3.14 -m venv .venv`, then install development tools with `.venv/bin/python -m pip install -e '.[dev]'`.

- `.venv/bin/python -m pytest tests/unit`: run the fast, database-free suite.
- `.venv/bin/python -m ruff check .`: check lint rules.
- `.venv/bin/python -m ruff format --check .`: verify formatting without changing files.
- `.venv/bin/python -m mypy src tests`: check types.
- `.venv/bin/python -m build`: build distribution files.
- `.venv/bin/moneywiz-cli /path/to/database.sqlite`: open the interactive, read-only shell.

## Coding Style & Naming Conventions

Use four-space indentation, double-quoted strings, and Ruff's 88-character line limit. Name modules and functions in `snake_case`, classes in `PascalCase`, and tests `test_*.py` with `test_*` functions. When adding a public `Record` field, add its mapping to the relevant schema profile and test its conversion; `SchemaProfile.validate()` checks that every public field is mapped.

## Testing Guidelines

Use pytest and favor focused unit tests with row dictionaries or temporary SQLite databases. Integration tests are opt-in: set `MONEYWIZ_TEST_DB_PATH` to an absolute path to a disposable MoneyWiz database, then run `.venv/bin/python -m pytest tests`. They skip when the variable is unset. Do not use a live personal database. CI runs unit tests, Ruff, and mypy; no minimum coverage threshold is configured.

## Commit & Pull Request Guidelines

Recent commits use short subjects such as `Fix schema profile validation and record construction`; capitalization and prefixes vary. Write a brief imperative subject that names the change. In pull requests, explain behavior changes, list the checks run, and link a relevant issue when one exists. Include a CLI example when changing user-visible shell behavior.
