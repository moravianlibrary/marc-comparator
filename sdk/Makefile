PYTHON_BASE := python3.12

PYTHON_VENV := .venv
PYTHON := $(PYTHON_VENV)/bin/python
PYTHON_PIP := $(PYTHON_VENV)/bin/pip

PYTHON_DEPS := requirements.txt

ADDITIONAL_LIBS := coverage testcontainers pytest pytest-asyncio
TESTS_DIR := tests
target ?= not _smoke

.PHONY: generate-env remove-env regenerate-env test test-integration coverage-report run

generate-env:
	$(PYTHON_BASE) -m venv $(PYTHON_VENV)
	$(PYTHON) -m ensurepip
	$(PYTHON_PIP) install --upgrade pip
	$(PYTHON_PIP) install -r $(PYTHON_DEPS)
	$(PYTHON_PIP) install $(ADDITIONAL_LIBS)

remove-env:
	rm -rf $(PYTHON_VENV)

regenerate-env: remove-env generate-env

test:
	PYTHONPATH=. $(PYTHON) -m coverage run -m unittest discover -s $(TESTS_DIR) \
	&& $(PYTHON) -m coverage html \
	&& $(PYTHON) -m coverage report

test-integration:
	PYTHONPATH=. $(PYTHON) -m coverage run -m pytest $(TESTS_DIR)/integration -k "$(target)" \
	&& $(PYTHON) -m coverage html \
	&& $(PYTHON) -m coverage report

test-integration-verbose:
	PYTHONPATH=. $(PYTHON) -m pytest -s -vv $(TESTS_DIR)/integration -k "$(target)"

coverage-report:
	xdg-open htmlcov/index.html &

run:
	PYTHONPATH=. $(PYTHON) app.py