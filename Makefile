.PHONY: help env-base env-dev install check lint format typecheck test clean build

help:
	@echo "Starter — available commands:"
	@echo ""
	@echo "  Setup"
	@echo "    make env-dev     Create the development Conda environment"
	@echo "    make install     Install starter with development extras"
	@echo ""
	@echo "  Quality"
	@echo "    make check       Run all checks (lint + typecheck + test)"
	@echo "    make lint        Run Ruff linter"
	@echo "    make format      Auto-fix formatting with Ruff"
	@echo "    make typecheck   Run MyPy"
	@echo "    make test        Run pytest"
	@echo ""
	@echo "  Release"
	@echo "    make build       Build distribution packages"
	@echo "    make clean       Remove build and cache artifacts"

env-base:
	conda env create -f conda-recipes/base.yaml

env-dev:
	conda env create -f conda-recipes/dev.yaml

install:
	pip install -e ".[dev]"

check: lint typecheck test

lint:
	ruff check .
	ruff format --check .

format:
	ruff check . --fix
	ruff format .

typecheck:
	mypy starter

test:
	pytest

build:
	pip install hatch
	hatch build

clean:
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .ruff_cache .mypy_cache .hypothesis
	rm -rf .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
