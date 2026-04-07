"""Rich-backed console logging adapter."""

from __future__ import annotations

import logging
from importlib import import_module
from typing import Any

from ..core.schema import LoggingConfig


def build_rich_logger(*, name: str, cfg: LoggingConfig) -> logging.Logger:
    """Build a console logger using RichHandler."""
    try:
        RichHandler: Any = import_module("rich.logging").RichHandler
    except ImportError as exc:
        raise RuntimeError(
            "rich is not installed. Install starter with the 'logging-rich' extra."
        ) from exc

    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(cfg.level.upper())
    logger.propagate = False

    handler = RichHandler(
        level=cfg.level.upper(),
        rich_tracebacks=cfg.rich_tracebacks,
        show_path=cfg.show_path,
        markup=False,
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger
