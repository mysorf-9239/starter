# Sweeps Subsystem

## Overview

`starter.sweeps` standardizes hyperparameter search for ML and research workflows. It generates parameter combinations from a typed search space, executes trials through a `SweepRunner` backend, and aggregates results into a structured `SweepSummary`.

## Responsibilities

- define search space with typed parameter descriptors
- generate parameter combinations via grid or random strategies
- execute trials through a `SweepRunner` backend
- collect and aggregate results into `SweepSummary`
- integrate with `Tracker` and `ArtifactManager` from `RuntimeContext`
- support serialization of results to JSON

This subsystem is not responsible for:

- composing Hydra config
- managing training loops or model code
- owning experiment-specific business logic

## Architecture

```text
starter/sweeps/
├── __init__.py              # Public API
├── core/
│   ├── schema.py            # SearchSpace, SweepsConfig, SweepResult, SweepSummary
│   ├── interfaces.py        # SweepRunner Protocol, TrialFn
│   ├── strategies.py        # GridStrategy, RandomStrategy
│   ├── factory.py           # build_sweep_runner, run_sweep
│   └── validate.py          # validate_sweeps_config
└── backends/
    ├── local.py             # LocalRunner — sequential execution
    └── wandb.py             # WandbRunner — delegate to wandb sweep agent
```

## Config Contract

Root config groups live under [`conf/sweeps/`](../../conf/sweeps/).

Supported backends: `local`, `wandb`

Supported strategies: `grid`, `random`

| Field | Type | Default | Description |
|---|---|---|---|
| `backend` | `str` | `"local"` | Execution backend |
| `strategy` | `str` | `"grid"` | Override generation strategy |
| `n_trials` | `int \| null` | `null` | Number of trials (required for `random`) |
| `seed` | `int \| null` | `null` | Random seed for reproducibility |
| `fail_fast` | `bool` | `false` | Stop on first trial failure |
| `enabled` | `bool` | `true` | Enable/disable the subsystem |

## Public API

```python
from starter.sweeps import (
    CategoricalParam,
    FloatParam,
    IntegerParam,
    SearchSpace,
    SweepResult,
    SweepRunner,
    SweepSummary,
    SweepsConfig,
    TrialFn,
    build_sweep_runner,
    run_sweep,
)
```

## Search Space

Define the hyperparameter search space using typed parameter descriptors:

```python
from starter.sweeps import SearchSpace, CategoricalParam, IntegerParam, FloatParam

space = SearchSpace(params=[
    CategoricalParam(name="optimizer", values=["adam", "sgd"]),
    FloatParam(name="lr", low=1e-4, high=1e-2, log_scale=True, n_points=5),
    IntegerParam(name="batch_size", low=16, high=128, step=16),
])
```

### Parameter types

| Type | Fields | Description |
|---|---|---|
| `CategoricalParam` | `name`, `values` | Fixed list of discrete values |
| `IntegerParam` | `name`, `low`, `high`, `step=1` | Integer range |
| `FloatParam` | `name`, `low`, `high`, `log_scale=False`, `n_points=10` | Float range |

## Trial Function

The `TrialFn` signature is:

```python
TrialFn = Callable[[RuntimeContext, Mapping[str, Any]], dict[str, float]]
```

Each trial receives a `RuntimeContext` and a parameter mapping for the current trial, and returns a metrics dict:

```python
def trial_fn(ctx, params):
    loss = train_model(
        lr=float(params["lr"]),
        optimizer=str(params["optimizer"]),
    )
    ctx.logger.info(f"trial loss={loss}")
    return {"loss": loss}
```

## Strategies

### Grid strategy

Generates all Cartesian product combinations:

```python
space = SearchSpace(params=[
    CategoricalParam(name="lr", values=[0.001, 0.01]),
    CategoricalParam(name="dropout", values=[0.1, 0.3]),
])
# Produces 4 trials: (0.001, 0.1), (0.001, 0.3), (0.01, 0.1), (0.01, 0.3)
```

### Random strategy

Samples `n_trials` combinations uniformly at random:

```python
cfg = SweepsConfig(strategy="random", n_trials=10, seed=42)
```

## Usage

### Via `run_sweep` (recommended)

```python
from starter.runtime import bootstrap
from starter.sweeps import SearchSpace, CategoricalParam, SweepsConfig, run_sweep

with bootstrap() as ctx:
    space = SearchSpace(params=[
        CategoricalParam(name="lr", values=[0.001, 0.01, 0.1]),
    ])
    cfg = SweepsConfig(strategy="grid")

    def trial_fn(ctx, params):
        loss = train_model(lr=float(params["lr"]))
        return {"loss": loss}

    summary = run_sweep(space, trial_fn, ctx, cfg)
    best = summary.best_trial("loss", mode="min")
    ctx.logger.info(f"Best: {best.override_set}, loss={best.metrics['loss']}")
```

### Via `build_sweep_runner` (manual)

```python
from starter.sweeps import build_sweep_runner, SweepsConfig
from starter.sweeps.core.strategies import GridStrategy

cfg = SweepsConfig(backend="local", strategy="grid")
runner = build_sweep_runner(cfg)
override_sets = GridStrategy().generate(space)
summary = runner.run(override_sets, trial_fn)
```

## `SweepSummary`

| Member | Type | Description |
|---|---|---|
| `results` | `list[SweepResult]` | All trial results |
| `n_success` | `int` (property) | Number of successful trials |
| `n_failed` | `int` (property) | Number of failed trials |
| `best_trial(metric, mode)` | `SweepResult` | Best trial by metric (`"min"` or `"max"`) |
| `to_dataframe()` | `DataFrame \| list[dict]` | Returns `pd.DataFrame` if pandas is installed, else `list[dict]` |
| `to_json()` | `str` | Serialize to JSON string |
| `SweepSummary.from_json(s)` | `SweepSummary` | Deserialize from JSON string |

## `SweepResult` fields

| Field | Type | Description |
|---|---|---|
| `trial_index` | `int` | Zero-based trial index |
| `override_set` | `list[str]` | Hydra override strings for this trial |
| `status` | `str` | `"success"` or `"failed"` |
| `metrics` | `dict[str, float]` | Metrics returned by `trial_fn` |
| `error` | `str \| None` | Error message if `status == "failed"` |
| `created_at` | `datetime` | UTC creation timestamp |

## Backends

### Local

- stdlib only, no extra dependencies
- executes trials sequentially in the current process
- integrates with `Tracker` and `ArtifactManager` from `RuntimeContext`

### WandB

- extra: `tracking-wandb`
- delegates to `wandb.sweep()` and `wandb.agent()`
- requires `search_space` to be passed to `build_sweep_runner()`

```bash
pip install -e ".[tracking-wandb]"
```

## Design Rules

- Keep `TrialFn` signature consistent: `(RuntimeContext, Mapping[str, Any]) -> dict[str, float]`.
- Keep strategy logic pure — no side effects.
- Keep tracker and artifact manager integration in the runner, not in callers.
- Keep backend dependencies optional.
