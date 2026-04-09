"""RuntimeContext dataclass for the runtime subsystem."""

from __future__ import annotations

from dataclasses import dataclass

from starter.artifacts.core.interfaces import ArtifactManager
from starter.config.core.schema import AppConfig
from starter.logging.core.interfaces import Logger
from starter.profiling.core.interfaces import Profiler
from starter.tracking.core.interfaces import Tracker


@dataclass(frozen=True)
class RuntimeContext:
    """Immutable container holding all subsystem instances produced by bootstrap.

    Supports the context manager protocol: ``__exit__`` calls
    :func:`~starter.runtime.teardown` automatically.
    """

    cfg: AppConfig
    run_id: str
    logger: Logger
    tracker: Tracker
    profiler: Profiler
    artifact_manager: ArtifactManager

    def __enter__(self) -> RuntimeContext:
        return self

    def __exit__(self, *args: object) -> None:
        from .bootstrap import teardown

        teardown(self)
