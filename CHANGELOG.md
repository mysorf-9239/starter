# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.1.0] — 2026-04-07

### Added

- `starter.config`: Hydra/OmegaConf composition, typed `AppConfig` schema,
  validation, secret redaction, and OmegaConf path resolvers.
- `starter.logging`: logger factory with `console`, `file`, `rich`, and
  `structlog` backends.
- `starter.tracking`: experiment tracker with `wandb` backend and `NullTracker`.
- `starter.profiling`: lightweight tabular data profiling with `basic` and
  `pandas` backends.
- `starter.runtime`: `bootstrap()` entry point returning an immutable
  `RuntimeContext`; context manager and `teardown()` support.
- `starter.artifacts`: structured artifact save/load/list/delete with
  versioning strategies (`run_id`, `epoch`, `timestamp`, `manual`) and
  optional tracker upload integration.
- `starter.sweeps`: hyperparameter search with grid and random strategies,
  `LocalRunner`, `WandbRunner`, `SweepSummary`, and `TrialFn` protocol.
- `AppConfig` with sections for all seven subsystems.
- `RuntimeContext` with `cfg`, `logger`, `tracker`, `profiler`, and
  `artifact_manager` fields.
- Bundled `conf/` directory inside the package for correct path resolution
  after `pip install`.
- Subsystem `README.md` for all seven subsystems.
- Property-based tests via `hypothesis` for all subsystems.
- Conda environment recipes (`base.yaml`, `dev.yaml`).
- `Makefile` for local workflow commands.
- `ruff`, `mypy`, `pre-commit`, and `bandit` tooling configuration.
- GitHub Actions workflows for CI and automated release.
- `CITATION.cff` for academic citation.

[Unreleased]: https://github.com/mysorf-9239/starter/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mysorf-9239/starter/releases/tag/v0.1.0
