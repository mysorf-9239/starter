# Tracking Subsystem

## Overview

`starter.tracking` provides experiment-style tracking for ML and research workflows. It defines a thin abstraction over tracking backends so callers can log run metadata, metrics, and artifacts without coupling to a specific provider.

## Responsibilities

- define the tracking config schema
- validate backend-specific tracking config
- expose a minimal `Tracker` protocol
- construct a tracker implementation from a config section
- isolate provider-specific SDK usage inside backend modules

## Architecture

```text
starter/tracking/
├── __init__.py
├── core/
│   ├── factory.py     # build_tracker, parse_tracking_config
│   ├── interfaces.py  # Tracker Protocol
│   ├── schema.py      # TrackingConfig, WandbTrackingConfig
│   └── validate.py    # validate_tracking_config
└── backends/
    ├── null.py        # NullTracker — no-op
    └── wandb.py       # WandbTracker — Weights & Biases
```

## Config Contract

Root config groups live under [`conf/tracking/`](../../conf/tracking/).

Supported backends: `disabled`, `wandb`

### `TrackingConfig` fields

| Field | Type | Default | Description |
|---|---|---|---|
| `backend` | `str` | `"disabled"` | Tracking backend |
| `enabled` | `bool` | `false` | Enable/disable tracking |
| `run_name` | `str \| null` | `null` | Default run name |
| `save_config` | `bool` | `true` | Save config to tracker on run start |

### `WandbTrackingConfig` fields (`wandb.*`)

| Field | Type | Default | Description |
|---|---|---|---|
| `project` | `str \| null` | `null` | Weights & Biases project name |
| `entity` | `str \| null` | `null` | Weights & Biases entity/team |
| `api_key` | `str \| null` | `null` | API key (use `oc.env`) |
| `mode` | `str` | `"disabled"` | `online`, `offline`, or `disabled` |
| `tags` | `list[str]` | `[]` | Run tags |
| `group` | `str \| null` | `null` | Run group |
| `job_type` | `str \| null` | `null` | Job type label |
| `notes` | `str \| null` | `null` | Run notes |

## Public API

```python
from starter.tracking import (
    TrackingConfig,
    NullTracker,
    build_tracker,
    parse_tracking_config,
    validate_tracking_config,
)
```

### `Tracker` Protocol

```python
class Tracker(Protocol):
    def start_run(self, *, run_name: str | None = None) -> None: ...
    def log_params(self, params: Mapping[str, Any]) -> None: ...
    def log_metrics(self, metrics: Mapping[str, float], *, step: int | None = None) -> None: ...
    def log_artifact(self, path: str, *, name: str | None = None) -> None: ...
    def finish(self) -> None: ...
```

## Usage

### Via `RuntimeContext` (recommended)

```python
from starter.runtime import bootstrap

with bootstrap(["tracking=wandb"]) as ctx:
    ctx.tracker.start_run(run_name="baseline")
    ctx.tracker.log_params({"lr": 0.001, "epochs": 100})
    ctx.tracker.log_metrics({"loss": 0.42, "auroc": 0.91}, step=1)
    # finish() is called automatically on context exit
```

### Direct construction

```python
from starter.tracking import build_tracker, TrackingConfig

cfg = TrackingConfig(backend="disabled")
tracker = build_tracker(cfg)
tracker.start_run()
```

## Backends

### Disabled / Null

- no-op implementation
- no external dependencies
- suitable for local runs and tests

### Weights & Biases

- extra: `tracking-wandb`
- lazy-imports the `wandb` SDK
- supports `online`, `offline`, and `disabled` modes

```bash
pip install -e ".[tracking-wandb]"
```

Credentials via environment variables:

```bash
export WANDB_PROJECT=my-project
export WANDB_ENTITY=my-team
export WANDB_API_KEY=your-key
export WANDB_MODE=online
```

## Secret Handling

Secrets must not be committed to `conf/`. The default `wandb.yaml` reads credentials from the environment:

```yaml
wandb:
  api_key: ${oc.env:WANDB_API_KEY,null}
  mode: ${oc.env:WANDB_MODE,offline}
  project: ${oc.env:WANDB_PROJECT,starter}
  entity: ${oc.env:WANDB_ENTITY,null}
```

## Validation Rules

- `backend` must be one of the supported backends
- `disabled` backend requires `enabled: false`
- WandB backend requires `project` when `enabled: true`
- WandB `mode` must be `disabled`, `offline`, or `online`
- `online` mode requires `WANDB_API_KEY` to be set

## Design Rules

- Keep the `Tracker` protocol backend-agnostic.
- Keep provider SDK imports inside backend modules only.
- Keep backend dependencies optional.
- Keep run lifecycle explicit: `start_run()` → `finish()`.
