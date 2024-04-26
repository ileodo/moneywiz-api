
VENV?=${VIRTUAL_ENV}
PYTHONPATH=./src


${VENV}/bin/activate:
	python3.10 -m venv ${VENV}

venv: ${VENV}/bin/activate

install: requirements.txt requirements-dev.txt venv
	${VENV}/bin/pip3 install -r requirements.txt
	${VENV}/bin/pip3 install -r requirements-dev.txt

test:
	${VENV}/bin/python -m pytest tests

pylint:
	${VENV}/bin/python -m pylint --rcfile .pylintrc src

mypy:
	${VENV}/bin/python -m mypy src

format:
	${VENV}/bin/python -m black -l 88 src tests

shell:
	${VENV}/bin/python src/moneywiz_api/cli/cli.py

package:
	${VENV}/bin/python -m build

test-publish:
	${VENV}/bin/python -m twine upload --repository testpypi dist/*

publish:
	${VENV}/bin/python -m twine upload --repository pypi dist/*
