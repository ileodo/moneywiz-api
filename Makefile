
VENV?=${VIRTUAL_ENV}

${VENV}/bin/activate:
	python3.10 -m venv ${VENV}

venv: ${VENV}/bin/activate

install: pyproject.toml venv
	${VENV}/bin/pip3 install -e .[dev]

test:
	${VENV}/bin/python -m pytest tests

ruff:
	${VENV}/bin/python -m ruff check

mypy:
	${VENV}/bin/python -m mypy src

format:
	${VENV}/bin/python -m ruff format

shell:
	${VENV}/bin/python src/moneywiz_api/cli/cli.py

package:
	${VENV}/bin/python -m build

test-publish:
	${VENV}/bin/python -m twine upload --repository testpypi dist/*

publish:
	${VENV}/bin/python -m twine upload --repository pypi dist/*
