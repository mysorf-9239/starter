# Config Subsystem

## Overview

`starter.config` is the configuration composition layer for the `starter` library. It is the only subsystem permitted to interact with Hydra composition directly. All other subsystems receive their config section from a higher-level caller.

## Responsibilities

- compose application config from Hydra config groups under `conf/`
- merge composed config into a typed `AppConfig` schema
- validate cross-cutting runtime invariants
- resolve shared path conventions via OmegaConf resolvers
- redact known secrets before rendering config
- expose a library API and a CLI entrypoint

## Architecture

```text
starter/config/
├── __init__.py
├── core/
│   ├── compose.py     # compose_config, compose_typed_config, to_yaml, redact_secrets
│   ├── registry.py    # register_config_store
│   ├── resolvers.py   # OmegaConf custom resolvers
│   ├── schema.py      # AppConfig, AppSection, EnvSection, PathsSection, RuntimeSection
│   └── validate.py    # validate_config
└── docs/
    └── EXTENDING.md   # Extension guide for new subsystems
```

## Public API

```python
from starter.config import (
    AppConfig,
    compose_config,
    compose_typed_config,
    redact_secrets,
    register_config_store,
    to_yaml,
    validate_config,
)
```

| Symbol | Description |
|---|---|
| `compose_config(overrides)` | Returns raw `DictConfig` |
| `compose_typed_config(overrides)` | Returns typed `AppConfig` (validates by default) |
| `to_yaml(overrides)` | Renders composed config as a YAML string |
| `redact_secrets(cfg)` | Renders config with known secrets masked |
| `validate_config(cfg)` | Validates paths, runtime, and tracking invariants |
| `register_config_store()` | Registers structured config schemas with Hydra's ConfigStore |
| `AppConfig` | Typed top-level config dataclass |

## AppConfig Schema

```python
@dataclass
class AppConfig:
    app: AppSection          # name, subsystem, version
    env: EnvSection          # workspace, name, platform
    paths: PathsSection      # repo_root, config_root, output_dir, artifacts_dir, cache_dir
    runtime: RuntimeSection  # debug, seed, strict_config, profile
    logging: dict            # owned by starter.logging
    tracking: dict           # owned by starter.tracking
    profiling: dict          # owned by starter.profiling
    artifacts: dict          # owned by starter.artifacts
    sweeps: dict             # owned by starter.sweeps
```

### `RuntimeSection` defaults

| Field | Type | Default | Description |
|---|---|---|---|
| `debug` | `bool` | `false` | Enable debug mode |
| `seed` | `int` | `7` | Global random seed |
| `strict_config` | `bool` | `true` | Fail on unknown config keys |
| `profile` | `str` | `"default"` | Execution profile name |

## Usage

### Compose config programmatically

```python
from starter.config import compose_typed_config

cfg = compose_typed_config(["env=ci", "logging=structlog", "runtime.seed=42"])
print(cfg.runtime.seed)   # 42
print(cfg.env.name)       # "ci"
```

### Render config as YAML

```python
from starter.config import to_yaml

print(to_yaml(["tracking=wandb"]))
```

### Redact secrets before logging

```python
from starter.config import compose_typed_config, redact_secrets

cfg = compose_typed_config(["tracking=wandb"])
print(redact_secrets(cfg))  # tracking.wandb.api_key: ***REDACTED***
```

### CLI entrypoint

```bash
starter-config logging=console tracking=disabled runtime.seed=42
```

## Secret Handling

Secrets must not be committed to `conf/`. Use `oc.env` interpolation in YAML:

```yaml
# conf/tracking/wandb.yaml
wandb:
  api_key: ${oc.env:WANDB_API_KEY,null}
```

Known secret paths masked by `redact_secrets()`:
- `tracking.wandb.api_key`

## Design Rules

- `starter.config` is the only composition layer.
- Subsystem schemas stay in the owning subsystem.
- Secrets live in environment variables, not committed YAML.
- Public imports are shallow through `starter.config`.
- Validation fails early with clear messages.
