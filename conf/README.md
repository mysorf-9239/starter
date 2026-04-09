# Config Groups Reference

## Overview

[`conf/`](./) is the Hydra configuration source for the `starter` library. Config groups are kept at the repository root
so that defaults and environment profiles are visible at the top level and downstream bootstrap code has a single,
predictable location to reference.

## Layout

```text
conf/
├── config.yaml      # Primary defaults list
├── env/             # Environment profiles
├── paths/           # Shared path conventions
├── runtime/         # Execution-mode flags
├── logging/         # Logging backend configs
├── tracking/        # Tracking backend configs
├── profiling/       # Profiling backend configs
├── artifacts/       # Artifacts backend configs
├── sweeps/          # Sweeps backend configs
└── hydra/           # Hydra runtime behavior
```

## `config.yaml`

Primary defaults list. Selects the default group member for each top-level section.

```yaml
defaults:
  - _self_
  - env: local
  - paths: default
  - runtime: default
  - logging: console
  - tracking: disabled
  - profiling: basic
  - artifacts: default
  - sweeps: default
  - hydra: default

app:
  name: starter
  subsystem: config
  version: 0.1.1
```

## Group Reference

### `env/`

Environment selection profiles.

| File         | Use case                       |
|--------------|--------------------------------|
| `local.yaml` | Local development              |
| `dev.yaml`   | Shared development environment |
| `ci.yaml`    | Continuous integration         |

### `paths/`

Shared filesystem path conventions resolved at runtime.

| Key             | Description                         |
|-----------------|-------------------------------------|
| `repo_root`     | Absolute path to repository root    |
| `config_root`   | Absolute path to `conf/`            |
| `output_dir`    | Default output directory            |
| `artifacts_dir` | Default artifacts storage directory |
| `cache_dir`     | Local cache directory               |

### `runtime/`

Execution-mode flags and global settings.

| Key             | Default     | Description                 |
|-----------------|-------------|-----------------------------|
| `debug`         | `false`     | Enable debug mode           |
| `seed`          | `7`         | Global random seed          |
| `strict_config` | `true`      | Fail on unknown config keys |
| `profile`       | `"default"` | Execution profile name      |

### `logging/`

Logging configuration groups passed to `starter.logging`.

| File             | Backend       | Dependencies                            |
|------------------|---------------|-----------------------------------------|
| `disabled.yaml`  | No-op         | None                                    |
| `console.yaml`   | stdlib stdout | None                                    |
| `file.yaml`      | stdlib file   | None                                    |
| `rich.yaml`      | Rich          | `pip install -e ".[logging-rich]"`      |
| `structlog.yaml` | structlog     | `pip install -e ".[logging-structlog]"` |

### `tracking/`

Tracking configuration groups passed to `starter.tracking`.

| File            | Backend          | Dependencies                         |
|-----------------|------------------|--------------------------------------|
| `disabled.yaml` | No-op            | None                                 |
| `wandb.yaml`    | Weights & Biases | `pip install -e ".[tracking-wandb]"` |

Credentials are read from environment variables:

```bash
export WANDB_PROJECT=my-project
export WANDB_API_KEY=your-key
export WANDB_MODE=online
```

### `profiling/`

Profiling configuration groups passed to `starter.profiling`.

| File            | Backend | Dependencies                           |
|-----------------|---------|----------------------------------------|
| `disabled.yaml` | No-op   | None                                   |
| `basic.yaml`    | stdlib  | None                                   |
| `pandas.yaml`   | pandas  | `pip install -e ".[profiling-pandas]"` |

### `artifacts/`

Artifacts configuration groups passed to `starter.artifacts`.

| File           | Backend | Description              |
|----------------|---------|--------------------------|
| `default.yaml` | `local` | Local filesystem storage |

Key fields: `backend`, `enabled`, `base_dir`, `versioning_strategy`

### `sweeps/`

Sweeps configuration groups passed to `starter.sweeps`.

| File           | Backend | Description                |
|----------------|---------|----------------------------|
| `default.yaml` | `local` | Sequential local execution |

Key fields: `backend`, `strategy`, `n_trials`, `seed`, `fail_fast`

### `hydra/`

Hydra runtime behavior: run directory convention, sweep directory convention, and `chdir` behavior.

## Config Ownership Model

`conf/` defines selection and defaults and is the source-of-truth config tree. Schema meaning belongs to the owning
subsystem.

| Config group | Owned by                                              |
|--------------|-------------------------------------------------------|
| `logging/`   | [`starter.logging`](../starter/logging/README.md)     |
| `tracking/`  | [`starter.tracking`](../starter/tracking/README.md)   |
| `profiling/` | [`starter.profiling`](../starter/profiling/README.md) |
| `artifacts/` | [`starter.artifacts`](../starter/artifacts/README.md) |
| `sweeps/`    | [`starter.sweeps`](../starter/sweeps/README.md)       |

## Rules

- Secrets must not be committed to `conf/`. Use `oc.env` interpolation for credentials and let `starter.config` load
  `.env` files into the environment.
- New top-level groups should correspond to real, reusable subsystems.
- Defaults must be explicit in `config.yaml`.
- Config values must not contain business logic.

## Adding a New Subsystem

1. Create a new group directory under `conf/`.
2. Add a `default.yaml` with sensible defaults.
3. Add the group to the `defaults` list in `config.yaml`.
4. Implement the subsystem under `starter/`.
5. Document the subsystem in its own `README.md`.
