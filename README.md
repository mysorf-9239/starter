# Starter

`starter` is a reusable Python foundation providing shared infrastructure subsystems for ML and research projects. Each subsystem is independently usable and follows a consistent internal convention.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Subsystems

| Subsystem | Status | Description |
|---|---|---|
| [`config`](starter/config/README.md) | Stable | Hydra/OmegaConf composition, typed schema, validation |
| [`logging`](starter/logging/README.md) | Stable | Logger factory with 4 backends |
| [`tracking`](starter/tracking/README.md) | Stable | Experiment tracker with Weights & Biases backend |
| [`profiling`](starter/profiling/README.md) | Stable | Lightweight tabular data profiling |
| [`runtime`](starter/runtime/README.md) | Stable | Bootstrap orchestration, `RuntimeContext` |
| [`artifacts`](starter/artifacts/README.md) | Stable | Artifact save/load/version management |
| [`sweeps`](starter/sweeps/README.md) | Stable | Hyperparameter search (grid, random, wandb) |

## Installation

### From GitHub

```bash
pip install git+https://github.com/mysorf-9239/starter.git
```

Pin to a specific release:

```bash
pip install git+https://github.com/mysorf-9239/starter.git@v0.1.0
```

### With optional extras

```bash
# Rich terminal logging
pip install "starter[logging-rich] @ git+https://github.com/mysorf-9239/starter.git"

# Weights & Biases tracking
pip install "starter[tracking-wandb] @ git+https://github.com/mysorf-9239/starter.git"

# All optional backends
pip install "starter[all] @ git+https://github.com/mysorf-9239/starter.git"
```

### In pyproject.toml

```toml
[project]
dependencies = [
    "starter @ git+https://github.com/mysorf-9239/starter.git@v0.1.0",
]

[project.optional-dependencies]
ml = [
    "starter[tracking-wandb,logging-rich] @ git+https://github.com/mysorf-9239/starter.git@v0.1.0",
]
```

### Local editable install

```bash
git clone https://github.com/mysorf-9239/starter.git
cd starter
conda env create -f conda-recipes/dev.yaml
conda activate starter
pip install -e ".[dev]"
```

## Quick Start

```python
from starter.runtime import bootstrap

with bootstrap(["logging=rich", "tracking=wandb"]) as ctx:
    ctx.logger.info("experiment started")
    ctx.tracker.start_run(run_name="baseline")
    ctx.tracker.log_metrics({"loss": 0.42}, step=1)
```

### Hyperparameter sweep

```python
from starter.runtime import bootstrap
from starter.sweeps import SearchSpace, CategoricalParam, SweepsConfig, run_sweep

with bootstrap() as ctx:
    space = SearchSpace(params=[
        CategoricalParam(name="lr", values=[0.001, 0.01, 0.1]),
    ])

    def trial_fn(ctx, params):
        loss = train_model(lr=float(params["lr"]))
        return {"loss": loss}

    summary = run_sweep(space, trial_fn, ctx, SweepsConfig(strategy="grid"))
    best = summary.best_trial("loss", mode="min")
```

## CLI

```bash
# Inspect the composed config
starter

# With overrides
starter logging=structlog tracking=wandb runtime.seed=42

# Debug mode
starter runtime=debug
```

## Repository Layout

```text
starter/
├── conf/                # Root Hydra config groups
│   ├── config.yaml      # Primary defaults list
│   ├── env/             # Environment profiles (local, dev, ci)
│   ├── paths/           # Shared path conventions
│   ├── runtime/         # Execution-mode flags
│   ├── logging/         # Logging backend configs
│   ├── tracking/        # Tracking backend configs
│   ├── profiling/       # Profiling backend configs
│   ├── artifacts/       # Artifacts backend configs
│   └── sweeps/          # Sweeps backend configs
├── conda-recipes/       # Conda environments
├── starter/             # Python package
│   ├── config/          # Config composition layer
│   ├── logging/         # Logging subsystem
│   ├── tracking/        # Tracking subsystem
│   ├── profiling/       # Profiling subsystem
│   ├── runtime/         # Bootstrap orchestration
│   ├── artifacts/       # Artifact management
│   ├── sweeps/          # Hyperparameter search
│   └── cli.py           # `starter-config` CLI entrypoint
├── tests/               # Test suite (pytest + hypothesis)
├── docs/                # Repository-level design documents
├── pyproject.toml       # Packaging and tool configuration
└── Makefile             # Local workflow commands
```

## Subsystem Layout Convention

Every subsystem follows the same internal structure:

```text
subsystem/
├── __init__.py       # Shallow public API exports
├── README.md         # Usage and API reference
├── core/
│   ├── schema.py     # @dataclass config schema and data models
│   ├── interfaces.py # Protocol definitions
│   ├── factory.py    # build_xxx() + parse_xxx_config()
│   └── validate.py   # validate_xxx_config()
└── backends/         # Concrete implementations
```

## Optional Extras

| Extra | Installs | Enables |
|---|---|---|
| `logging-rich` | `rich` | Rich terminal output |
| `logging-structlog` | `structlog` | Structured/JSON logging |
| `tracking-wandb` | `wandb` | Weights & Biases experiment tracking |
| `profiling-pandas` | `pandas` | DataFrame-based profiling |

```bash
pip install -e ".[logging-rich,tracking-wandb]"
```

## Development

```bash
make check    # ruff + mypy
make format   # ruff format --fix
pytest -q     # run test suite
pre-commit run --all-files  # full CI check
```

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — layering model and dependency direction
- [`docs/BOOTSTRAP.md`](docs/BOOTSTRAP.md) — integration guide for downstream projects
- [`conf/README.md`](conf/README.md) — Hydra config group reference

## Citation

If this software is used in research, please cite it using the metadata below
or via the [`CITATION.cff`](CITATION.cff) file.

```bibtex
@software{starter2026,
  author  = {Nguyen, Duc Danh},
  title   = {Starter: Reusable Python Infrastructure Subsystems},
  year    = {2026},
  version = {0.1.0},
  url     = {https://github.com/mysorf-9239/starter},
  license = {MIT}
}
```

## License

[MIT License](LICENSE) — Copyright (c) 2026 Nguyen Duc Danh (Mysorf)
