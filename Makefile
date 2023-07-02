

MONEYWIZ_DB_PATH?="/Users/$(shell whoami)/Library/Containers/com.moneywiz.personalfinance/Data/Documents/.AppData/ipadMoneyWiz.sqlite"

.venv/bin/activate:
	python3.10 -m venv .venv

venv: .venv/bin/activate

install: requirements.txt requirements-dev.txt venv
	.venv/bin/pip3 install -r requirements.txt
	.venv/bin/pip3 install -r requirements-dev.txt

test:
	.venv/bin/python -m pytest tests

pylint:
	.venv/bin/python -m pylint --rcfile .pylintrc src

mypy:
	.venv/bin/python -m mypy src

format:
	.venv/bin/python -m black -l 88 src tests

shell:
	.venv/bin/python src/moneywiz_api/shell.py ${MONEYWIZ_DB_PATH}

package:
	.venv/bin/python -m build

publish:
	.venv/bin/python -m twine upload --repository testpypi dist/*
