"""Interfaces for the profiling subsystem."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from .schema import ProfileSummary


class Profiler(Protocol):
    """Minimal profiler interface for tabular records."""

    def profile_records(self, records: Sequence[Mapping[str, Any]]) -> ProfileSummary: ...
