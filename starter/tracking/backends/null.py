"""No-op Tracker implementation for the disabled backend."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class NullTracker:
    """No-op Tracker returned when tracking is disabled.

    All methods accept the same arguments as the :class:`Tracker` protocol
    and discard them without side effects.
    """

    def start_run(self, *, run_name: str | None = None) -> None:
        del run_name

    def log_params(self, params: Mapping[str, Any]) -> None:
        del params

    def log_metrics(self, metrics: Mapping[str, float], *, step: int | None = None) -> None:
        del metrics
        del step

    def log_artifact(self, path: str, *, name: str | None = None) -> None:
        del path
        del name

    def finish(self) -> None:
        return None
