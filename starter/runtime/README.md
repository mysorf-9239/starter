# Runtime Subsystem

## Overview

`starter.runtime` is the bootstrap orchestration subsystem of the `starter` library. It provides a single `bootstrap()` entry point that composes configuration and constructs all subsystem instances, returning an immutable `RuntimeContext` for injection into application code.

## Responsibilities

- compose Hydra config via `starter.config`
- build `Logger`, `Tracker`, `Profiler`, and `ArtifactManager` instances
- package all instances into an immutable `RuntimeContext`
- manage resource teardown via `teardown()` and context manager support

This subsystem is not responsible for:

- composing config independently (delegates to `starter.config`)
- owning business or experiment logic
- managing training loops or pipelines

## Architecture

```text
starter/runtime/
├── __init__.py          # Public API: RuntimeContext, bootstrap, teardown
└── core/
    ├── schema.py        # RuntimeContext frozen dataclass + context manager
    └── bootstrap.py     # bootstrap() + teardown()
```

### Bootstrap sequence

```text
bootstrap(overrides)
    1. compose_typed_config(overrides)              → AppConfig
    2. build_logger(cfg.logging, name=cfg.app.name) → Logger
    3. build_tracker(cfg.tracking)                  → Tracker
    4. build_profiler(cfg.profiling)                → Profiler
    5. build_artifact_manager(cfg.artifacts,
                              cfg.paths,
                              tracker=tracker)      → ArtifactManager
    → RuntimeContext(cfg, logger, tracker, profiler, artifact_manager)
```

## Public API

```python
from starter.runtime import bootstrap, teardown, RuntimeContext
```

| Symbol | Description |
|---|---|
| `bootstrap(overrides)` | Compose config and build all subsystem instances |
| `teardown(context)` | Release resources (calls `tracker.finish()`) |
| `RuntimeContext` | Immutable container with all subsystem instances |

## RuntimeContext

`RuntimeContext` is a `frozen=True` dataclass. All fields are immutable after construction.

| Field | Type | Source |
|---|---|---|
| `cfg` | `AppConfig` | `starter.config.compose_typed_config()` |
| `logger` | `Logger` Protocol | `starter.logging.build_logger()` |
| `tracker` | `Tracker` Protocol | `starter.tracking.build_tracker()` |
| `profiler` | `Profiler` Protocol | `starter.profiling.build_profiler()` |
| `artifact_manager` | `ArtifactManager` Protocol | `starter.artifacts.build_artifact_manager()` |

`RuntimeContext` supports the context manager protocol. `__exit__` calls `teardown()` automatically.

## Usage

### Context manager (recommended)

```python
from starter.runtime import bootstrap

with bootstrap(["logging=rich", "tracking=wandb"]) as ctx:
    ctx.logger.info("started")
    ctx.tracker.start_run(run_name="exp-01")
    # teardown() is called automatically on exit
```

### Manual teardown

```python
from starter.runtime import bootstrap, teardown

ctx = bootstrap()
ctx.logger.info("started")
ctx.tracker.start_run(run_name="exp-01")
teardown(ctx)
```

### Hydra overrides

```python
with bootstrap(["runtime.seed=42", "logging=structlog", "tracking=disabled"]) as ctx:
    ctx.logger.info(f"seed={ctx.cfg.runtime.seed}")
```

### Disabled backends (for tests)

```python
ctx = bootstrap(["logging=disabled", "tracking=disabled", "profiling=disabled"])
# ctx.logger   → NullLogger
# ctx.tracker  → NullTracker
# ctx.profiler → NullProfiler
```

## Error Handling

Exceptions from any bootstrap step propagate directly without wrapping. `teardown()` suppresses exceptions from `tracker.finish()` and emits a warning via `context.logger` to avoid masking a caller exception.

## Design Rules

- `bootstrap()` is the only place that imports from all subsystems.
- Subsystems do not import each other.
- `RuntimeContext` uses Protocol interfaces only — no concrete backend classes.
