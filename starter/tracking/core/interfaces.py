"""Interfaces for the tracking subsystem."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class Tracker(Protocol):
    """Minimal tracker interface for experiment-style workflows."""

    def start_run(self, *, run_name: str | None = None) -> None: ...

    def log_params(self, params: Mapping[str, Any]) -> None: ...

    def log_metrics(self, metrics: Mapping[str, float], *, step: int | None = None) -> None: ...

    def log_artifact(self, path: str, *, name: str | None = None) -> None: ...

    def finish(self) -> None: ...
