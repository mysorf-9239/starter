"""Console logging backend."""

from __future__ import annotations

import logging
import sys


def build_console_logger(*, name: str, level: str, fmt: str) -> logging.Logger:
    """Build a stdout-backed logger."""
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(level.upper())
    logger.propagate = False

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    return logger
