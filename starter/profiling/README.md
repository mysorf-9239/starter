# Profiling Subsystem

## Overview

`starter.profiling` provides lightweight tabular data profiling for reusable pipelines and research workflows. It produces structured `ProfileSummary` objects that other layers can inspect, log, track, or persist.

## Responsibilities

- define profiling schema and summary models
- validate profiling config
- expose a minimal `Profiler` protocol
- construct a profiler implementation from a config section
- return structured `ProfileSummary` objects

## Architecture

```text
starter/profiling/
├── __init__.py
├── core/
│   ├── factory.py     # build_profiler, parse_profiling_config, NullProfiler
│   ├── interfaces.py  # Profiler Protocol
│   ├── schema.py      # ProfilingConfig, ProfileSummary, ColumnProfile, NumericSummary
│   └── validate.py    # validate_profiling_config
└── backends/
    ├── basic.py       # stdlib-only tabular profiler
    └── pandas.py      # pandas DataFrame profiler
```

## Config Contract

Root config groups live under [`conf/profiling/`](../../conf/profiling/).

Supported backends: `disabled`, `basic`, `pandas`

| Field | Type | Default | Description |
|---|---|---|---|
| `backend` | `str` | `"basic"` | Profiling backend |
| `enabled` | `bool` | `true` | Enable/disable profiling |
| `top_k` | `int` | `5` | Top-K most frequent values per column |
| `numeric_stats` | `bool` | `true` | Compute min/max/mean for numeric columns |
| `sample_size` | `int \| null` | `null` | Limit rows before profiling (no limit when `null`) |

## Public API

```python
from starter.profiling import (
    ProfilingConfig,
    ProfileSummary,
    NullProfiler,
    build_profiler,
    parse_profiling_config,
    validate_profiling_config,
)
```

### `Profiler` Protocol

```python
class Profiler(Protocol):
    def profile_records(self, records: Sequence[Mapping[str, Any]]) -> ProfileSummary: ...
```

### `ProfileSummary` fields

| Field | Type | Description |
|---|---|---|
| `row_count` | `int` | Total number of rows |
| `column_count` | `int` | Total number of columns |
| `columns` | `list[ColumnProfile]` | Per-column statistics |

### `ColumnProfile` fields

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Column name |
| `non_null_count` | `int` | Non-null row count |
| `null_count` | `int` | Null row count |
| `unique_count` | `int` | Unique value count |
| `sample_values` | `list[str]` | Top-K most frequent values |
| `numeric` | `NumericSummary \| None` | Min/max/mean (numeric columns only) |

### `NumericSummary` fields

| Field | Type | Description |
|---|---|---|
| `count` | `int` | Non-null numeric row count |
| `minimum` | `float \| None` | Minimum value |
| `maximum` | `float \| None` | Maximum value |
| `mean` | `float \| None` | Arithmetic mean |

## Usage

### Via `RuntimeContext` (recommended)

```python
from starter.runtime import bootstrap

with bootstrap(["profiling=basic"]) as ctx:
    summary = ctx.profiler.profile_records([
        {"drug": "A", "score": 1.2},
        {"drug": "B", "score": 0.9},
    ])
    ctx.logger.info(f"rows={summary.row_count}, cols={summary.column_count}")
    ctx.tracker.log_metrics({"profile_rows": float(summary.row_count)})
```

### Direct construction

```python
from starter.profiling import build_profiler, ProfilingConfig

cfg = ProfilingConfig(backend="basic", top_k=3)
profiler = build_profiler(cfg)
summary = profiler.profile_records(records)
```

## Backends

### Disabled

- no-op implementation
- no external dependencies

### Basic

- stdlib only, no extra dependencies
- input: `Sequence[Mapping[str, Any]]` (Python dicts)
- suitable for lightweight profiling without dataframe dependencies

### Pandas

- extra: `profiling-pandas`
- input: `Sequence[Mapping[str, Any]]`
- suitable when the calling project already uses pandas

```bash
pip install -e ".[profiling-pandas]"
```

## Design Rules

- Keep the summary model backend-neutral.
- Keep profiling pure where possible — no side effects.
- Keep backend dependencies optional.
- Keep logging and tracking concerns in the caller, not in this subsystem.
