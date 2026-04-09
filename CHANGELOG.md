# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.1] — 2026-04-09

### Added

- Built-in `.env` loading in `starter.config` before Hydra composition.
- Runtime-generated `run_id` exposed on `RuntimeContext`.
- Tests covering `.env` precedence, runtime `run_id`, sweeps teardown, and
  WandB sweep strategy mapping.

### Changed

- Root `conf/` is now the source-of-truth config tree for the project.
- Packaging now force-includes root `conf/` into the wheel at `starter/conf`.
- `starter.artifacts` now aligns the default `run_id` versioning strategy with
  runtime bootstrap behavior.
- `starter.sweeps` local trials now always tear down their bootstrapped
  runtime context.
- `starter.sweeps` WandB backend now respects `grid` vs `random` strategy and
  uses `n_trials` for random-agent execution.
- Logging validation is now side-effect free; file path creation happens only
  in backend builders.

### Fixed

- Validation for typed `ArtifactsConfig` inputs is now consistent with mapping
  and `DictConfig` inputs.
- Disabled artifacts config now rejects `enabled=true` when
  `backend=\"disabled\"`.
- Tracking dependency-missing tests no longer depend on the host environment's
  `wandb` installation state.
- Documentation now consistently references the `starter` CLI and the updated
  runtime/config contract.

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

---

## [Unreleased]
---

[0.1.1]: https://github.com/mysorf-9239/starter/releases/tag/v0.1.1

[0.1.0]: https://github.com/mysorf-9239/starter/releases/tag/v0.1.0

[Unreleased]: https://github.com/mysorf-9239/starter/compare/v0.1.1...HEAD
