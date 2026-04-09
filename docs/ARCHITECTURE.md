# Architecture

## Overview

`starter` is a reusable Python foundation for shared infrastructure subsystems that can be integrated into multiple ML
and research projects. The architecture is organized into distinct layers with clear ownership boundaries, keeping
subsystem cores decoupled so they can be reused independently of any single application shape.

## Design Principles

| Principle                | Description                                                              |
|--------------------------|--------------------------------------------------------------------------|
| Single composition layer | Only `starter.config` composes the root Hydra config                     |
| Subsystem ownership      | Each subsystem owns its schema, validation, and factory                  |
| Decoupled cores          | Subsystems do not import from each other                                 |
| Optional providers       | External SDK imports are confined to backend modules and optional extras |
| Bootstrap wiring         | Cross-subsystem integration occurs exclusively in `starter.runtime`      |
| Protocol interfaces      | Subsystems expose Protocol types, not concrete backend classes           |

## Repository Structure

```text
starter/
├── conf/                 # Root Hydra config groups
├── conda-recipes/        # Conda environments
├── docs/                 # Repository-level design documents
├── starter/              # Python package
│   ├── config/           # Config composition layer
│   ├── logging/          # Logging subsystem
│   ├── tracking/         # Tracking subsystem
│   ├── profiling/        # Profiling subsystem
│   ├── artifacts/        # Artifact management subsystem
│   ├── runtime/          # Bootstrap orchestration layer
│   ├── sweeps/           # Hyperparameter search subsystem
│   └── cli.py            # `starter` CLI entrypoint
├── tests/
├── pyproject.toml
└── README.md
```

## Layering Model

### Layer 1 — Config

Owned by [`starter/config/`](../starter/config/README.md).

The only subsystem permitted to interact with Hydra composition directly.

Responsibilities:

- compose root Hydra config from `conf/` groups
- expose typed `AppConfig` schema
- validate shared invariants
- resolve shared paths and redact secrets

### Layer 2 — Subsystems

Each subsystem accepts only its own config section, passed from the bootstrap layer. No subsystem composes config or
imports from another subsystem.

| Subsystem           | Owns                                                          |
|---------------------|---------------------------------------------------------------|
| `starter.logging`   | `LoggingConfig`, `Logger` Protocol, 4 backends                |
| `starter.tracking`  | `TrackingConfig`, `Tracker` Protocol, wandb backend           |
| `starter.profiling` | `ProfilingConfig`, `Profiler` Protocol, basic/pandas backends |
| `starter.artifacts` | `ArtifactsConfig`, `ArtifactManager` Protocol, local backend  |
| `starter.sweeps`    | `SweepsConfig`, `SweepRunner` Protocol, local/wandb backends  |

Each subsystem follows the same internal layout:

```text
subsystem/
├── core/
│   ├── schema.py      # @dataclass config + data models
│   ├── interfaces.py  # Protocol definitions
│   ├── factory.py     # build_xxx() + parse_xxx_config()
│   └── validate.py    # validate_xxx_config()
└── backends/          # Concrete implementations
```

### Layer 3 — Runtime (Bootstrap)

Owned by [`starter/runtime/`](../starter/runtime/README.md).

The single integration point for all subsystems.

Responsibilities:

- call `starter.config.compose_typed_config()`
- build all subsystem instances in the correct order
- package them into an immutable `RuntimeContext`
- manage resource teardown

## Dependency Direction

```text
downstream project
    └── starter.runtime.bootstrap()
            ├── starter.config      (compose_typed_config)
            ├── starter.logging     (build_logger)
            ├── starter.tracking    (build_tracker)
            ├── starter.profiling   (build_profiler)
            └── starter.artifacts   (build_artifact_manager)
```

`starter.sweeps` is used independently — it receives a `RuntimeContext` from the caller and does not participate in the
bootstrap sequence.

Subsystem-to-subsystem hard dependencies are prohibited:

- `starter.logging` must not import `starter.config`
- `starter.tracking` must not import `starter.logging`
- `starter.profiling` must not push summaries into a tracker directly

## Config Ownership Model

```text
conf/                    ← defines selection and defaults
    config.yaml          ← primary defaults list
    logging/             ← owned by starter.logging
    tracking/            ← owned by starter.tracking
    profiling/           ← owned by starter.profiling
    artifacts/           ← owned by starter.artifacts
    sweeps/              ← owned by starter.sweeps
```

`AppConfig` in `starter.config` holds lightweight references to each subsystem section as `dict[str, Any]`. Detailed
schema meaning stays in the owning subsystem.

## Public API Strategy

Downstream projects import from subsystem package roots only:

```python
from starter.config import compose_typed_config, AppConfig
from starter.logging import build_logger
from starter.tracking import build_tracker
from starter.profiling import build_profiler
from starter.artifacts import build_artifact_manager, ArtifactType
from starter.runtime import bootstrap, RuntimeContext
from starter.sweeps import run_sweep, SearchSpace, SweepsConfig
```

Internal modules under `core/` and `backends/` are implementation details and are not part of the public API.

## Optional Dependencies

| Extra               | Library     | Subsystem                            |
|---------------------|-------------|--------------------------------------|
| `logging-rich`      | `rich`      | `starter.logging`                    |
| `logging-structlog` | `structlog` | `starter.logging`                    |
| `tracking-wandb`    | `wandb`     | `starter.tracking`, `starter.sweeps` |
| `profiling-pandas`  | `pandas`    | `starter.profiling`                  |

## Stability Boundaries

### Stable

- config composition flow
- subsystem factory pattern
- `core/` + `backends/` layout convention
- `RuntimeContext` shape
- `starter.artifacts` path conventions
- `starter.sweeps` strategy and runner interfaces

### Expected to grow

- additional storage backends for artifacts (S3, GCS)
- additional tracking backends (MLflow)
- domain-oriented subsystems (evaluation, data validation)
- distributed sweep execution

## Recommended Downstream Usage

1. Add `starter` as a dependency.
2. Call `bootstrap()` once in the project entry point.
3. Pass `RuntimeContext` into pipelines and training loops.
4. Use `run_sweep()` for hyperparameter search.
5. Extend `starter` only for cross-project infrastructure.
