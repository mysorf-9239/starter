"""Local sequential implementation of the SweepRunner protocol."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ..core.interfaces import TrialFn
from ..core.schema import SweepResult, SweepSummary

if TYPE_CHECKING:
    from starter.artifacts.core.interfaces import ArtifactManager
    from starter.tracking.core.interfaces import Tracker

logger = logging.getLogger(__name__)


def _parse_params(override_set: list[str]) -> dict[str, Any]:
    """Convert a list of ``key=value`` strings into a typed parameter mapping.

    Entries that do not contain ``=`` are silently skipped.  String values
    that parse as ``int`` or ``float`` are promoted to the corresponding
    numeric type; all other values remain as ``str``.

    Args:
        override_set: List of ``"key=value"`` strings.

    Returns:
        Mapping from parameter names to their parsed values.
    """
    params: dict[str, Any] = {}
    for item in override_set:
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        try:
            params[k] = int(v)
        except ValueError:
            try:
                params[k] = float(v)
            except ValueError:
                params[k] = v
    return params


class LocalRunner:
    """SweepRunner that executes trials sequentially on the local machine.

    For each trial, the runner:

    1. Parses the override set into a typed ``params`` mapping.
    2. Calls ``bootstrap(base_overrides)`` to obtain a fresh
       :class:`RuntimeContext`.
    3. Invokes ``trial_fn(ctx, params)``, supplying both the infrastructure
       context and the parsed hyperparameter mapping.
    4. Records the outcome and optionally forwards metrics to the tracker and
       persists the sweep summary via the artifact manager.

    Hyperparameters are delivered through ``params`` rather than as Hydra
    overrides, allowing arbitrary keys that are not present in the config
    schema.
    """

    def __init__(
        self,
        base_overrides: list[str],
        fail_fast: bool = False,
        tracker: Tracker | None = None,
        artifact_manager: ArtifactManager | None = None,
    ) -> None:
        """Initialise the runner.

        Args:
            base_overrides: Hydra override strings applied to every trial
                bootstrap call.
            fail_fast: When ``True``, execution stops after the first failed
                trial.
            tracker: Optional tracker for logging per-trial params and metrics.
            artifact_manager: Optional artifact manager for persisting the
                sweep summary.
        """
        self._base_overrides = base_overrides
        self._fail_fast = fail_fast
        self._tracker = tracker
        self._artifact_manager = artifact_manager

    def run(
        self,
        override_sets: list[list[str]],
        trial_fn: TrialFn,
    ) -> SweepSummary:
        """Execute all trials and return the aggregated summary.

        Args:
            override_sets: One list of ``"key=value"`` strings per trial.
            trial_fn: Callable with signature
                ``(RuntimeContext, Mapping[str, Any]) -> dict[str, float]``.

        Returns:
            :class:`SweepSummary` containing one :class:`SweepResult` per
            trial.
        """
        from starter.runtime import bootstrap

        results: list[SweepResult] = []

        for idx, override_set in enumerate(override_sets):
            params = _parse_params(override_set)

            if self._tracker is not None:
                try:
                    self._tracker.log_params({"trial_index": idx, **params})
                except Exception as exc:  # noqa: BLE001
                    logger.warning("tracker.log_params() failed for trial %d: %s", idx, exc)

            try:
                ctx = bootstrap(self._base_overrides)
                metrics = trial_fn(ctx, params)
                result = SweepResult(
                    trial_index=idx,
                    override_set=override_set,
                    status="success",
                    metrics=metrics,
                    created_at=datetime.utcnow(),
                )
                if self._tracker is not None:
                    try:
                        self._tracker.log_metrics(metrics, step=idx)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("tracker.log_metrics() failed for trial %d: %s", idx, exc)
            except Exception as exc:  # noqa: BLE001
                result = SweepResult(
                    trial_index=idx,
                    override_set=override_set,
                    status="failed",
                    error=str(exc),
                    created_at=datetime.utcnow(),
                )
                if self._fail_fast:
                    results.append(result)
                    break

            results.append(result)

        summary = SweepSummary(results=results)

        if self._artifact_manager is not None:
            try:
                import tempfile
                from pathlib import Path

                from starter.artifacts.core.schema import ArtifactType

                with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                    f.write(summary.to_json())
                    tmp_path = f.name
                self._artifact_manager.save(
                    Path(tmp_path),
                    name="sweep_summary",
                    artifact_type=ArtifactType.OUTPUT,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("artifact_manager.save() failed for sweep summary: %s", exc)

        return summary
