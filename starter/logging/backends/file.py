"""File logging backend."""

from __future__ import annotations

import logging
from pathlib import Path


def build_file_logger(*, name: str, level: str, fmt: str, path: str) -> logging.Logger:
    """Build a file-backed logger."""
    log_path = Path(path).expanduser().resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(level.upper())
    logger.propagate = False

    handler = logging.FileHandler(log_path)
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    return logger
