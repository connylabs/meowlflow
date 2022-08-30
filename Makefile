.PHONY: black black-test clean clean-build clean-pyc clean-test coverage docs flake8 help install test e2e
define BROWSER_PYSCRIPT
import os, webbrowser, sys
try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT
BROWSER := python -c "$$BROWSER_PYSCRIPT"
VERSION := `cat VERSION`
PROJECT := "meowlflow"
SRC := $(shell find . -type f -name '*.py' | grep -v '^./.eggs')
BIN_DIR := bin
BASH_UNIT := $(shell pwd)/$(BIN_DIR)/bash_unit
BASH_UNIT_FLAGS :=

help:
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test and coverage artifacts"
	@echo "test - run tests quickly with the default Python"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "docs - generate documentation"
	@echo "install - install the package to the active Python's site-packages"

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	find . -name '.mypy_cache' -exec rm -fr {} +

clean-test:
	rm -f .coverage
	rm -fr htmlcov/

test:
	poetry run pytest --cov=$(PROJECT) --cov-report=html --cov-report=term-missing  --verbose tests

coverage:
	coverage run --source $(PROJECT) setup.py test
	coverage report -m
	coverage html
	$(BROWSER) htmlcov/index.html

install:
	pip install .

docs: README.md

flake8:
	poetry run flake8 $(SRC)

black:
	poetry run black -t py39 $(SRC)

black-test:
	poetry run black -t py39 $(SRC) --check

README.md: $(SRC)
	@perl -i -n0e 'while(/(.*?)^(\[replace\]:\s*#\s*\(([^\n]*)\)\n```[^\n]*\n).*?^(```)$$(.*?)/smg){print "$$1$$2"; open (FILE, "<", "$$3") or die "could not open file: $$3\n";print <FILE>;close (FILE); print "$$4\n$$5"}' $@

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

$(BASH_UNIT): | $(BIN_DIR)
	curl -Lo $@ https://raw.githubusercontent.com/pgrange/bash_unit/v1.7.2/bash_unit
	chmod +x $@

e2e: $(BASH_UNIT)
	$(BASH_UNIT) $(BASH_UNIT_FLAGS) ./e2e/meowlflow.sh
