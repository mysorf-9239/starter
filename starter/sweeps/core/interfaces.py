"""Interfaces for the sweeps subsystem."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any, Protocol

from .schema import SweepSummary

if TYPE_CHECKING:
    from starter.runtime.core.schema import RuntimeContext

# Canonical trial function signature:
#   ctx:    RuntimeContext  — fully initialised infrastructure (logger, tracker,
#                             artifact_manager, cfg)
#   params: dict[str, Any]  — hyperparameter values for the current trial
#   returns: dict[str, float] — metrics produced by the trial
TrialFn = Callable[["RuntimeContext", Mapping[str, Any]], dict[str, float]]


class SweepRunner(Protocol):
    """Minimal sweep runner interface."""

    def run(
        self,
        override_sets: list[list[str]],
        trial_fn: TrialFn,
    ) -> SweepSummary: ...
