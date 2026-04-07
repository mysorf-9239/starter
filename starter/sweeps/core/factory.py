"""Factory functions and high-level API for the sweeps subsystem."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from .interfaces import SweepRunner
from .schema import SearchSpace, SweepsConfig, SweepSummary
from .validate import validate_sweeps_config

if TYPE_CHECKING:
    from starter.artifacts.core.interfaces import ArtifactManager
    from starter.runtime.core.schema import RuntimeContext
    from starter.tracking.core.interfaces import Tracker


def build_sweep_runner(
    config: SweepsConfig,
    base_overrides: list[str] | None = None,
    tracker: Tracker | None = None,
    artifact_manager: ArtifactManager | None = None,
    search_space: SearchSpace | None = None,
) -> SweepRunner:
    """Construct a :class:`SweepRunner` from a config section.

    Args:
        config: :class:`SweepsConfig` controlling backend and strategy.
        base_overrides: Hydra override strings applied to every trial bootstrap
            call.
        tracker: Optional tracker for logging per-trial params and metrics.
        artifact_manager: Optional artifact manager for persisting the sweep
            summary.
        search_space: Required when ``config.backend`` is ``"wandb"``.

    Returns:
        A :class:`SweepRunner` instance for the configured backend.

    Raises:
        ValueError: If the backend identifier is not supported, or if
            *search_space* is absent for the WandB backend.
    """
    validate_sweeps_config(config)

    from ..backends.local import LocalRunner

    if config.backend == "local":
        return LocalRunner(
            base_overrides=base_overrides or [],
            fail_fast=config.fail_fast,
            tracker=tracker,
            artifact_manager=artifact_manager,
        )

    if config.backend == "wandb":
        from ..backends.wandb import WandbRunner

        if search_space is None:
            raise ValueError("search_space is required for WandB backend.")
        return WandbRunner(search_space=search_space)

    raise ValueError(
        f"Unsupported sweeps backend: {config.backend!r}. Valid options: ['local', 'wandb']"
    )


def _generate_override_sets(space: SearchSpace, config: SweepsConfig) -> list[list[str]]:
    """Generate override sets from *space* using the strategy in *config*.

    Args:
        space: Hyperparameter search space.
        config: Sweep configuration specifying strategy and trial count.

    Returns:
        List of override sets, one per trial.
    """
    from .strategies import GridStrategy, RandomStrategy

    if config.strategy == "grid":
        return GridStrategy().generate(space)
    n = config.n_trials or 1
    return RandomStrategy(n_trials=n, seed=config.seed).generate(space)


def run_sweep(
    search_space: SearchSpace,
    trial_fn: Callable[..., dict[str, float]],
    ctx: RuntimeContext,
    config: SweepsConfig,
) -> SweepSummary:
    """Generate override sets, execute all trials, and return the aggregated summary.

    The *trial_fn* signature must be::

        def trial_fn(ctx: RuntimeContext, params: Mapping[str, Any]) -> dict[str, float]: ...

    A fresh :class:`RuntimeContext` is bootstrapped for each trial using the
    base overrides from the runner.  Hyperparameters are delivered through
    *params* rather than as Hydra overrides, allowing arbitrary keys that are
    absent from the config schema.

    Args:
        search_space: Hyperparameter search space defining the trial grid.
        trial_fn: Callable receiving a :class:`RuntimeContext` and a parsed
            parameter mapping, returning a metrics dict.
        ctx: :class:`RuntimeContext` providing the sweep-level tracker and
            artifact manager.
        config: :class:`SweepsConfig` controlling strategy and backend.

    Returns:
        :class:`SweepSummary` containing one :class:`SweepResult` per trial.

    Raises:
        ValueError: If *config* fails validation.

    Example::

        def trial_fn(ctx, params):
            loss = train(lr=float(params["lr"]))
            return {"loss": loss}

        summary = run_sweep(space, trial_fn, ctx, SweepsConfig(strategy="grid"))
        best = summary.best_trial("loss", mode="min")
    """
    validate_sweeps_config(config)
    override_sets = _generate_override_sets(search_space, config)

    runner = build_sweep_runner(
        config=config,
        tracker=ctx.tracker,
        artifact_manager=ctx.artifact_manager,
        search_space=search_space,
    )
    return runner.run(override_sets, trial_fn)
