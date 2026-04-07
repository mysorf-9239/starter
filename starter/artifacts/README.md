# Artifacts Subsystem

## Overview

`starter.artifacts` provides a structured abstraction for saving, loading, listing, deleting, and resolving paths for ML and research workflow artifacts — including model checkpoints, datasets, output files, and result directories.

## Responsibilities

- define the artifact config schema
- validate artifact backend configuration
- expose a minimal `ArtifactManager` protocol
- construct concrete artifact manager implementations from a config section
- support versioning strategies: `run_id`, `epoch`, `timestamp`, `manual`
- optionally upload artifacts to a remote tracker after saving

This subsystem is not responsible for:

- composing Hydra config
- logging progress independently
- tracking metrics remotely
- enforcing dataset-specific business rules

## Architecture

```text
starter/artifacts/
├── __init__.py              # Public API
├── core/
│   ├── exceptions.py        # ArtifactNotFoundError
│   ├── interfaces.py        # ArtifactManager Protocol
│   ├── schema.py            # ArtifactRecord, ArtifactType, ArtifactsConfig, VersioningStrategy
│   ├── factory.py           # build_artifact_manager, parse_artifacts_config
│   └── validate.py          # validate_artifacts_config
└── backends/
    ├── local.py             # LocalBackend — filesystem implementation
    └── null.py              # NullArtifactManager — no-op for tests
```

## Config Contract

Root config groups live under [`conf/artifacts/`](../../conf/artifacts/).

Supported backends: `local`, `disabled`

Supported versioning strategies: `run_id`, `epoch`, `timestamp`, `manual`

| Field | Type | Default | Description |
|---|---|---|---|
| `backend` | `str` | `"local"` | Storage backend |
| `enabled` | `bool` | `true` | Enable/disable the subsystem |
| `base_dir` | `str \| null` | `null` | Override default artifacts directory |
| `versioning_strategy` | `str` | `"run_id"` | Auto-version generation strategy |

## Public API

```python
from starter.artifacts import (
    ArtifactManager,
    ArtifactNotFoundError,
    ArtifactRecord,
    ArtifactType,
    ArtifactsConfig,
    NullArtifactManager,
    VersioningStrategy,
    build_artifact_manager,
    parse_artifacts_config,
)
```

### `ArtifactManager` Protocol

| Method | Signature | Description |
|---|---|---|
| `save` | `(source, name, artifact_type, version=None) -> ArtifactRecord` | Copy file/dir to structured path, return `ArtifactRecord` |
| `load` | `(name, artifact_type, version=None) -> Path` | Return `Path` to saved artifact (latest if version omitted) |
| `resolve_path` | `(name, artifact_type, version) -> Path` | Return expected path without creating anything |
| `list_artifacts` | `(artifact_type=None, name=None) -> list[ArtifactRecord]` | List saved artifacts with optional filters |
| `delete` | `(name, artifact_type, version) -> None` | Remove artifact from storage |

### `ArtifactRecord` fields

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Artifact name |
| `version` | `str` | Version string |
| `path` | `Path` | Absolute path to saved artifact |
| `artifact_type` | `ArtifactType` | Artifact classification |
| `size_bytes` | `int` | Size of saved artifact in bytes |
| `created_at` | `datetime` | UTC creation timestamp |

### `ArtifactType` values

| Value | String | Description |
|---|---|---|
| `ArtifactType.CHECKPOINT` | `"checkpoint"` | Model checkpoints |
| `ArtifactType.DATASET` | `"dataset"` | Dataset files |
| `ArtifactType.OUTPUT` | `"output"` | Output files |
| `ArtifactType.GENERIC` | `"generic"` | Unclassified artifacts |

## Path Convention

Artifacts are stored at:

```text
{base_dir}/{artifact_type}/{name}/{version}/{filename}
```

Example:

```text
artifacts/checkpoint/best_model/run_abc123/model.pt
artifacts/dataset/train_split/epoch_0005/train.csv
```

## Versioning Strategies

| Strategy | Behavior |
|---|---|
| `run_id` | Uses the `run_id` passed to the manager (required) |
| `epoch` | Formats integer version as `"epoch_{n:04d}"` |
| `timestamp` | Generates UTC timestamp `"YYYYMMDD_HHMMSS"` |
| `manual` | Requires explicit version string from caller |

## Usage

### Via `RuntimeContext` (recommended)

```python
from starter.runtime import bootstrap
from starter.artifacts import ArtifactType

with bootstrap() as ctx:
    record = ctx.artifact_manager.save(
        "model.pt",
        name="best_model",
        artifact_type=ArtifactType.CHECKPOINT,
    )
    ctx.logger.info(f"Saved to {record.path}")

    path = ctx.artifact_manager.load("best_model", ArtifactType.CHECKPOINT)
```

### Direct construction

```python
from starter.artifacts import build_artifact_manager, ArtifactsConfig
from starter.config import compose_typed_config

cfg = compose_typed_config()
mgr = build_artifact_manager(
    ArtifactsConfig(backend="local", versioning_strategy="manual"),
    cfg.paths,
    run_id="exp-01",
)
record = mgr.save("model.pt", "best_model", ArtifactType.CHECKPOINT, version="v1")
```

## Tracker Integration

When a `Tracker` is provided to `build_artifact_manager()`, `save()` automatically calls `tracker.log_artifact(path, name=name)` after saving. Exceptions from the tracker are suppressed and logged as warnings — the pipeline is never interrupted by tracker failures.

## Design Rules

- Keep the `ArtifactManager` protocol backend-agnostic.
- Keep backend dependencies optional.
- Keep `resolve_path()` a pure function with no side effects.
- Keep tracker integration in the backend, not in callers.
