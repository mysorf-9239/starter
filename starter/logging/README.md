# Logging Subsystem

## Overview

`starter.logging` owns logger construction for projects built on `starter`. It translates a logging config section into a concrete logger instance while keeping the rest of the system insulated from provider-specific details.

## Responsibilities

- define the logging config schema
- validate logging backend configuration
- expose a minimal `Logger` protocol
- construct concrete logger implementations from a config section

## Architecture

```text
starter/logging/
├── __init__.py
├── core/
│   ├── factory.py     # build_logger, parse_logging_config, NullLogger
│   ├── interfaces.py  # Logger Protocol
│   ├── schema.py      # LoggingConfig
│   └── validate.py    # validate_logging_config
└── backends/
    ├── console.py     # stdlib logging to stdout
    ├── file.py        # stdlib logging to file
    ├── rich.py        # Rich terminal output
    └── structlog.py   # Structured/JSON logging
```

## Config Contract

Root config groups live under [`conf/logging/`](../../conf/logging/).

Supported backends: `disabled`, `console`, `file`, `rich`, `structlog`

| Field | Type | Default | Description |
|---|---|---|---|
| `backend` | `str` | `"console"` | Logging backend |
| `enabled` | `bool` | `true` | Enable/disable logging |
| `level` | `str` | `"INFO"` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `format` | `str` | `"%(asctime)s \| %(levelname)s \| %(name)s \| %(message)s"` | Log format string |
| `path` | `str \| null` | `null` | Log file path (`file` backend only) |
| `json` | `bool` | `false` | JSON output (`file` or `structlog` backends only) |
| `context` | `dict` | `{}` | Bound context fields (`structlog` backend only) |
| `rich_tracebacks` | `bool` | `false` | Rich traceback rendering (`rich` backend only) |
| `show_path` | `bool` | `true` | Show file path in tracebacks (`rich` backend only) |

## Public API

```python
from starter.logging import (
    LoggingConfig,
    NullLogger,
    build_logger,
    parse_logging_config,
    validate_logging_config,
)
```

### `Logger` Protocol

```python
class Logger(Protocol):
    def debug(self, message: str) -> None: ...
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def exception(self, message: str) -> None: ...
```

## Usage

### Via `RuntimeContext` (recommended)

```python
from starter.runtime import bootstrap

with bootstrap(["logging=structlog"]) as ctx:
    ctx.logger.info("experiment started")
    ctx.logger.warning("low memory")
```

### Direct construction

```python
from starter.logging import build_logger, parse_logging_config

cfg = parse_logging_config({"backend": "console", "level": "DEBUG"})
logger = build_logger(cfg, name="my-app")
logger.info("hello")
```

### Disabled (for tests)

```python
from starter.logging import NullLogger

logger = NullLogger()
logger.info("no-op")
```

## Backends

### Disabled

- no-op implementation
- no external dependencies

### Console

- stdlib only, no extra dependencies
- writes to stdout with configurable format string

### File

- stdlib only
- requires `path` to be set
- supports JSON output with `json: true`

### Rich

- extra: `logging-rich`
- pretty terminal output with syntax highlighting and traceback rendering

```bash
pip install -e ".[logging-rich]"
```

### Structlog

- extra: `logging-structlog`
- structured, context-aware logging with JSON output support

```bash
pip install -e ".[logging-structlog]"
```

## Validation Rules

- `backend` must be one of the supported backends
- `level` must be a valid Python logging level
- `path` is required for the `file` backend
- `json` is only valid for `file` or `structlog` backends
- `rich` backend does not accept `path`

## Design Rules

- Keep the `Logger` protocol minimal.
- Keep backend selection in the factory, not in callers.
- Keep backend-specific dependencies optional.
- Keep filesystem side effects limited to backends that require them.
