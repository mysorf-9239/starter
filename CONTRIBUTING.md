# Contributing to Starter

This document describes how to set up a development environment, run quality
checks, and submit changes.

## Development Setup

```bash
git clone https://github.com/mysorf-9239/starter.git
cd starter
conda env create -f conda-recipes/dev.yaml
conda activate starter
pip install -e ".[dev]"
pre-commit install
```

## Running Checks

```bash
make lint        # ruff check + format check
make typecheck   # mypy
make test        # pytest
make check       # all of the above
pre-commit run --all-files  # full pre-commit pipeline
```

## Code Style

- Python 3.10+, `from __future__ import annotations` in every module.
- Type annotations required on all public functions (`disallow_untyped_defs = true`).
- Line length: 100 characters. Quote style: double. Enforced by `ruff`.
- No `assert` in production code — use explicit `if ... raise` guards.
- No bare `except` — use `except Exception` with `# noqa: BLE001` when intentional.
- Docstrings follow Google style with `Args`, `Returns`, and `Raises` sections.

## Subsystem Layout Convention

Every subsystem must follow the same internal structure:

```text
starter/<subsystem>/
├── __init__.py          # Shallow public API exports only
├── README.md            # Usage and API reference
├── core/
│   ├── schema.py        # @dataclass config schema and data models
│   ├── interfaces.py    # Protocol definitions
│   ├── factory.py       # build_xxx() + parse_xxx_config()
│   └── validate.py      # validate_xxx_config()
└── backends/            # Concrete implementations
```

A corresponding config group must be added under `conf/<subsystem>/` and
registered in `conf/config.yaml`.

## Adding a New Subsystem

1. Create the directory structure above.
2. Add a config group under `conf/<subsystem>/default.yaml`.
3. Add the group to the `defaults` list in `conf/config.yaml`.
4. Add the section to `AppConfig` in `starter/config/core/schema.py`.
5. Wire into `bootstrap()` in `starter/runtime/core/bootstrap.py`.
6. Add tests in `tests/test_<subsystem>.py` with unit and property-based tests.
7. Write a `README.md` for the subsystem.
8. Update `CHANGELOG.md` under `[Unreleased]`.

## Pull Request Guidelines

- Keep pull requests focused on a single concern.
- All checks must pass before review (`pre-commit run --all-files`).
- Add or update tests for any changed behavior.
- Update `CHANGELOG.md` under `[Unreleased]`.
- Reference related issues in the pull request description.

## Commit Message Format

```
<type>: <short summary>

<optional body>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

Examples:

```
feat: add sweeps subsystem with grid and random strategies
fix: resolve config path when installed via pip
docs: standardize subsystem README format
```

## Reporting Issues

Open an issue at https://github.com/mysorf-9239/starter/issues and include:

- A clear description of the problem or feature request.
- Steps to reproduce (for bugs).
- Expected vs actual behavior.
- Python version and OS.
