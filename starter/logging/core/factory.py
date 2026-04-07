"""Factory functions for constructing Logger instances from config."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from omegaconf import DictConfig, OmegaConf

from ..backends.console import build_console_logger
from ..backends.file import build_file_logger
from ..backends.rich import build_rich_logger
from ..backends.structlog import build_structlog_logger
from .interfaces import Logger
from .schema import LoggingConfig
from .validate import validate_logging_config


class NullLogger:
    """No-op Logger implementation returned when logging is disabled."""

    def debug(self, message: str) -> None:
        del message

    def info(self, message: str) -> None:
        del message

    def warning(self, message: str) -> None:
        del message

    def error(self, message: str) -> None:
        del message

    def exception(self, message: str) -> None:
        del message


def parse_logging_config(data: Mapping[str, Any] | DictConfig | LoggingConfig) -> LoggingConfig:
    """Parse and validate an external config mapping into a :class:`LoggingConfig`.

    Args:
        data: Raw config as a :class:`Mapping`, :class:`DictConfig`, or an
            already-typed :class:`LoggingConfig`.

    Returns:
        Validated :class:`LoggingConfig` instance.

    Raises:
        ValueError: If the config fails validation.
    """
    if isinstance(data, LoggingConfig):
        cfg = data
    elif isinstance(data, DictConfig):
        cfg = cast(
            LoggingConfig,
            OmegaConf.to_object(OmegaConf.merge(OmegaConf.structured(LoggingConfig), data)),
        )
    else:
        cfg = cast(
            LoggingConfig,
            OmegaConf.to_object(OmegaConf.merge(OmegaConf.structured(LoggingConfig), dict(data))),
        )
    validate_logging_config(cfg)
    return cfg


def build_logger(
    data: Mapping[str, Any] | DictConfig | LoggingConfig,
    *,
    name: str = "starter",
) -> Logger:
    """Construct a :class:`Logger` from a config section.

    Args:
        data: Logging config as a :class:`Mapping`, :class:`DictConfig`, or
            :class:`LoggingConfig`.
        name: Logger name passed to the backend.

    Returns:
        A :class:`Logger` instance for the configured backend, or a
        :class:`NullLogger` when the backend is ``"disabled"`` or
        ``enabled`` is ``False``.

    Raises:
        ValueError: If the backend identifier is not supported.
    """
    cfg = parse_logging_config(data)
    if cfg.backend == "disabled" or not cfg.enabled:
        return NullLogger()
    if cfg.backend == "console":
        return build_console_logger(name=name, level=cfg.level, fmt=cfg.format)
    if cfg.backend == "file" and cfg.path is not None:
        return build_file_logger(name=name, level=cfg.level, fmt=cfg.format, path=cfg.path)
    if cfg.backend == "rich":
        return build_rich_logger(name=name, cfg=cfg)
    if cfg.backend == "structlog":
        return build_structlog_logger(name=name, cfg=cfg)
    raise ValueError(f"Unsupported logging backend: {cfg.backend}")
