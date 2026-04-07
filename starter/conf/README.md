# Root Config Groups

## Purpose

[`conf/`](./) is the repository-level Hydra configuration source of truth.

This directory is kept at the repository root (not inside the Python package) so that:

- config groups are easy to discover during development
- defaults and environment profiles are visible at the top level
- downstream bootstrap code has one obvious place to look

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

## Group Roles

### `config.yaml`

Primary defaults list. Selects the default group for each top-level section.

```yaml
defaults:
  - env: local
  - paths: default
  - runtime: default
  - logging: console
  - tracking: disabled
  - profiling: basic
  - artifacts: default
  - sweeps: default
  - hydra: default
```

### `env/`

Environment selection:

| File | Use case |
|---|---|
| `local.yaml` | Local development |
| `dev.yaml` | Shared dev environment |
| `ci.yaml` | Continuous integration |

### `paths/`

Shared path conventions resolved at runtime:

| Key | Description |
|---|---|
| `repo_root` | Absolute path to repository root |
| `config_root` | Absolute path to `conf/` |
| `output_dir` | Default output directory |
| `artifacts_dir` | Default artifacts storage directory |
| `cache_dir` | Local cache directory |

### `runtime/`

Execution-mode flags:

| Key | Default | Description |
|---|---|---|
| `debug` | `false` | Enable debug mode |
| `seed` | `7` | Global random seed |
| `strict_config` | `true` | Fail on unknown config keys |
| `profile` | `"default"` | Execution profile name |

### `logging/`

Logging configuration groups passed into `starter.logging`.

| File | Backend | Dependencies |
|---|---|---|
| `disabled.yaml` | No-op | None |
| `console.yaml` | stdlib | None |
| `file.yaml` | stdlib | None |
| `rich.yaml` | Rich | `pip install -e ".[logging-rich]"` |
| `structlog.yaml` | structlog | `pip install -e ".[logging-structlog]"` |

### `tracking/`

Tracking configuration groups passed into `starter.tracking`.

| File | Backend | Dependencies |
|---|---|---|
| `disabled.yaml` | No-op | None |
| `wandb.yaml` | Weights & Biases | `pip install -e ".[tracking-wandb]"` |

Credentials are read from environment variables:

```bash
export WANDB_PROJECT=my-project
export WANDB_API_KEY=your-key
```

### `profiling/`

Profiling configuration groups passed into `starter.profiling`.

| File | Backend | Dependencies |
|---|---|---|
| `disabled.yaml` | No-op | None |
| `basic.yaml` | stdlib | None |
| `pandas.yaml` | pandas | `pip install -e ".[profiling-pandas]"` |

### `artifacts/`

Artifacts configuration groups passed into `starter.artifacts`.

| File | Backend | Description |
|---|---|---|
| `default.yaml` | `local` | Local filesystem storage |

Key fields: `backend`, `enabled`, `base_dir`, `versioning_strategy`

### `sweeps/`

Sweeps configuration groups passed into `starter.sweeps`.

| File | Backend | Description |
|---|---|---|
| `default.yaml` | `local` | Sequential local execution |

Key fields: `backend`, `strategy`, `n_trials`, `seed`, `fail_fast`

### `hydra/`

Hydra runtime behavior:

- run directory convention
- sweep directory convention
- `chdir` behavior

## Ownership Model

`conf/` defines **selection and defaults**.

Detailed schema meaning belongs to the owning subsystem:

| Config group | Owned by |
|---|---|
| `logging/` | `starter.logging` |
| `tracking/` | `starter.tracking` |
| `profiling/` | `starter.profiling` |
| `artifacts/` | `starter.artifacts` |
| `sweeps/` | `starter.sweeps` |

## Rules

- Never commit secrets to `conf/` — use `oc.env` for credentials
- Add new top-level groups only for real reusable subsystems
- Keep defaults explicit in `config.yaml`
- Avoid business logic in config values

## Extending

When adding a new subsystem:

1. Create a new group directory under `conf/`
2. Add a `default.yaml` with sensible defaults
3. Add the group to `config.yaml` defaults list
4. Implement the subsystem under `starter/`
5. Document the subsystem in its own `README.md`

For deeper extension rules, see:
[`starter/config/docs/EXTENDING.md`](../starter/config/docs/EXTENDING.md)
