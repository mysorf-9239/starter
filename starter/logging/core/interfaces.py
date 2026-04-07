"""Interfaces for the logging subsystem."""

from __future__ import annotations

from typing import Protocol


class Logger(Protocol):
    """Minimal logger interface for starter subsystems."""

    def debug(self, message: str) -> None: ...

    def info(self, message: str) -> None: ...

    def warning(self, message: str) -> None: ...

    def error(self, message: str) -> None: ...

    def exception(self, message: str) -> None: ...
