# Bootstrap Integration Guide

## Overview

This document describes how downstream projects integrate the subsystems provided by `starter`. The central contract is:

> Configuration is composed once. Subsystem instances are constructed once. Both are delivered to application code
> through an immutable `RuntimeContext`.

Leaf code must not re-compose configuration or instantiate infrastructure services independently.

## Bootstrap Sequence

```text
bootstrap(overrides)
    1. compose_typed_config(overrides)              → AppConfig
    2. generate runtime run_id                      → str
    3. build_logger(cfg.logging, name=cfg.app.name) → Logger
    4. build_tracker(cfg.tracking)                  → Tracker
    5. build_profiler(cfg.profiling)                → Profiler
    6. build_artifact_manager(cfg.artifacts,
                              cfg.paths,
                              tracker=tracker,
                              run_id=run_id)        → ArtifactManager
    → RuntimeContext(cfg, run_id, logger, tracker, profiler, artifact_manager)
```

## Minimal Integration

```python
from starter.runtime import bootstrap

with bootstrap() as ctx:
    ctx.logger.info(f"Starting: {ctx.cfg.app.name}")
    ctx.logger.info(f"run_id={ctx.run_id}")
    ctx.tracker.start_run(run_name="baseline")
    ctx.tracker.log_metrics({"loss": 0.42}, step=1)
```

`teardown()` is called automatically on context exit, invoking `tracker.finish()`.

## Hydra Overrides

Pass Hydra override strings to `bootstrap()` to select backends or modify parameters without editing config files:

```python
with bootstrap([
    "logging=structlog",
    "tracking=wandb",
    "runtime.seed=42",
]) as ctx:
    ...
```

## RuntimeContext Fields

| Field              | Type                       | Description                                                    |
|--------------------|----------------------------|----------------------------------------------------------------|
| `cfg`              | `AppConfig`                | Full typed configuration                                       |
| `run_id`           | `str`                      | Runtime-generated identifier for the current bootstrap session |
| `logger`           | `Logger` Protocol          | Logging backend instance                                       |
| `tracker`          | `Tracker` Protocol         | Tracking backend instance                                      |
| `profiler`         | `Profiler` Protocol        | Profiling backend instance                                     |
| `artifact_manager` | `ArtifactManager` Protocol | Artifact storage backend instance                              |

## Artifact Management

```python
from starter.artifacts import ArtifactType

with bootstrap() as ctx:
    record = ctx.artifact_manager.save(
        "model.pt",
        name="best_model",
        artifact_type=ArtifactType.CHECKPOINT,
    )
    ctx.logger.info(f"Saved checkpoint to {record.path}")

    path = ctx.artifact_manager.load("best_model", ArtifactType.CHECKPOINT)
```

## Hyperparameter Sweeps

`starter.sweeps` operates independently of the bootstrap sequence. A `RuntimeContext` is passed in to provide
sweep-level tracking and artifact management.

The `trial_fn` receives a fresh `RuntimeContext` and a parameter mapping for each trial:

```python
from starter.sweeps import SearchSpace, CategoricalParam, FloatParam, SweepsConfig, run_sweep

with bootstrap() as ctx:
    space = SearchSpace(params=[
        CategoricalParam(name="optimizer", values=["adam", "sgd"]),
        FloatParam(name="lr", low=1e-4, high=1e-2, log_scale=True, n_points=5),
    ])


    def trial_fn(ctx, params):
        loss = train_model(
            optimizer=params["optimizer"],
            lr=float(params["lr"]),
        )
        return {"loss": loss}


    summary = run_sweep(space, trial_fn, ctx, SweepsConfig(strategy="grid"))
    best = summary.best_trial("loss", mode="min")
    ctx.logger.info(f"Best trial: {best.override_set}")
```

## Manual Subsystem Construction

When `bootstrap()` is not appropriate, subsystems can be constructed individually by passing the relevant config
section:

```python
from starter.logging import build_logger
from starter.tracking import build_tracker
from starter.profiling import build_profiler
from starter.artifacts import build_artifact_manager

logger = build_logger(cfg.logging, name="app")
tracker = build_tracker(cfg.tracking)
profiler = build_profiler(cfg.profiling)
artifact_manager = build_artifact_manager(cfg.artifacts, cfg.paths, tracker=tracker)
```

## Testing

For tests, disable expensive backends to avoid external dependencies:

```python
ctx = bootstrap([
    "logging=disabled",
    "tracking=disabled",
    "profiling=basic",
    "artifacts.enabled=false",
])
```

As a pytest fixture:

```python
import pytest
from starter.runtime import bootstrap


@pytest.fixture
def ctx():
    with bootstrap(["logging=disabled", "tracking=disabled"]) as c:
        yield c
```

## Ownership Model

| Layer             | Responsibilities                                             |
|-------------------|--------------------------------------------------------------|
| `starter.runtime` | Config composition, subsystem construction, teardown         |
| Subsystems        | Parsing their own config section, constructing their backend |
| Domain code       | Business logic, pipelines, calls into subsystem instances    |

## Anti-Patterns

| Anti-pattern                                        | Reason to avoid                                                                    |
|-----------------------------------------------------|------------------------------------------------------------------------------------|
| Calling `compose_typed_config()` in multiple places | Configuration must be composed once                                                |
| Importing `wandb` directly in domain code           | Use `ctx.tracker` instead                                                          |
| Constructing `LocalBackend` directly in tests       | Use `NullArtifactManager` or `artifacts.enabled=false`                             |
| Reading `os.environ` for credentials in domain code | Use `oc.env` in config YAML; let `starter.config` load `.env` into the environment |
| Calling `tracker.finish()` manually                 | Use the context manager or `teardown()`                                            |

## Extension Criteria

Extend `starter` when:

- the functionality is cross-project infrastructure
- the subsystem can remain decoupled from business logic
- multiple projects will benefit from the same abstraction

Keep functionality in the downstream project when:

- it is domain-specific (e.g., domain-specific metrics or data schemas)
- it depends on application semantics
- it is unlikely to be reused outside one project
