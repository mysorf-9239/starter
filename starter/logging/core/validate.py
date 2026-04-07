"""Validation functions for LoggingConfig."""

from __future__ import annotations

from pathlib import Path

from .schema import LoggingConfig

_VALID_BACKENDS = {"disabled", "console", "file", "structlog", "rich"}
_VALID_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


def validate_logging_config(cfg: LoggingConfig) -> None:
    """Validate a :class:`LoggingConfig` instance.

    Args:
        cfg: Logging configuration to validate.

    Raises:
        ValueError: If any constraint is violated.
    """
    if cfg.backend not in _VALID_BACKENDS:
        raise ValueError(
            "logging.backend must be one of: disabled, console, file, structlog, rich."
        )
    if cfg.level.upper() not in _VALID_LEVELS:
        raise ValueError("logging.level must be one of: CRITICAL, ERROR, WARNING, INFO, DEBUG.")
    if cfg.backend == "disabled" and cfg.enabled:
        raise ValueError("logging.enabled must be false when backend is disabled.")
    if cfg.backend == "file":
        if not cfg.path:
            raise ValueError("logging.path is required when backend is file.")
        Path(cfg.path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    if cfg.json and cfg.backend not in {"file", "structlog"}:
        raise ValueError("logging.json is only supported for file or structlog backends.")
    if cfg.backend == "rich" and cfg.path is not None:
        raise ValueError("logging.path is not supported for the rich backend.")
