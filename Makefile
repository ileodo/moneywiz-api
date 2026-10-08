
PYTHON ?= python3.14
VENV ?= $(if $(VIRTUAL_ENV),$(VIRTUAL_ENV),.venv)
VENV_PYTHON = $(VENV)/bin/python

.PHONY: venv install test ruff mypy format shell package test-publish publish

$(VENV_PYTHON):
	$(PYTHON) -m venv "$(VENV)"

venv: $(VENV_PYTHON)
	@"$(VENV_PYTHON)" -c 'import sys; sys.exit(sys.version_info < (3, 10))' || { \
		echo "$(VENV) must use Python 3.10 or newer; recreate it or set VENV to another path." >&2; \
		exit 1; \
	}

install: venv
	"$(VENV_PYTHON)" -m pip install -e '.[dev]'

test: venv
	"$(VENV_PYTHON)" -m pytest tests

ruff: venv
	"$(VENV_PYTHON)" -m ruff check .

mypy: venv
	"$(VENV_PYTHON)" -m mypy src tests

format: venv
	"$(VENV_PYTHON)" -m ruff format .

shell: venv
	"$(VENV_PYTHON)" src/moneywiz_api/cli/cli.py

package: venv
	"$(VENV_PYTHON)" -m build

test-publish: venv
	"$(VENV_PYTHON)" -m twine upload --repository testpypi dist/*

publish: venv
	"$(VENV_PYTHON)" -m twine upload --repository pypi dist/*
