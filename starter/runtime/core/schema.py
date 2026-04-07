"""RuntimeContext dataclass for the runtime subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuntimeContext:
    """Immutable container holding all subsystem instances produced by bootstrap.

    All fields are typed as :class:`Any` to avoid importing concrete backend
    classes at module level; the actual types conform to the Protocol interfaces
    defined in each subsystem.

    Supports the context manager protocol: ``__exit__`` calls
    :func:`~starter.runtime.teardown` automatically.
    """

    cfg: Any
    logger: Any
    tracker: Any
    profiler: Any
    artifact_manager: Any

    def __enter__(self) -> RuntimeContext:
        return self

    def __exit__(self, *args: object) -> None:
        from .bootstrap import teardown

        teardown(self)
