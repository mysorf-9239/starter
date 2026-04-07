"""Structlog-backed logging adapter."""

from __future__ import annotations

import logging
import sys
from importlib import import_module
from pathlib import Path
from typing import Any

from ..core.schema import LoggingConfig


def build_structlog_logger(*, name: str, cfg: LoggingConfig) -> logging.Logger:
    """Build a stdlib logger configured through structlog processors."""
    try:
        structlog: Any = import_module("structlog")
    except ImportError as exc:
        raise RuntimeError(
            "structlog is not installed. Install starter with the 'logging-structlog' extra."
        ) from exc

    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    if cfg.json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(cfg.level.upper())
    logger.propagate = False

    if cfg.path:
        log_path = Path(cfg.path).expanduser().resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = logging.FileHandler(log_path)
    else:
        handler = logging.StreamHandler(sys.stdout)

    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    bound = structlog.get_logger(name)
    if cfg.context:
        bound = bound.bind(**cfg.context)
    return bound
