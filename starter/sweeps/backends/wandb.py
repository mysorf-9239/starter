"""WandB sweep agent implementation of the SweepRunner protocol."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from ..core.interfaces import TrialFn
from ..core.schema import SearchSpace, SweepResult, SweepsConfig, SweepSummary


def _to_wandb_config(space: SearchSpace) -> dict[str, Any]:
    """Convert a :class:`SearchSpace` to a wandb sweep ``parameters`` dict.

    Args:
        space: Hyperparameter search space to convert.

    Returns:
        Dict suitable for the ``parameters`` key of a wandb sweep config.
    """
    from ..core.schema import CategoricalParam, IntegerParam

    params: dict[str, Any] = {}
    for p in space.params:
        if isinstance(p, CategoricalParam):
            params[p.name] = {"values": list(p.values)}
        elif isinstance(p, IntegerParam):
            params[p.name] = {
                "distribution": "int_uniform",
                "min": p.low,
                "max": p.high - 1,
            }
        else:
            dist = "log_uniform_values" if p.log_scale else "uniform"
            params[p.name] = {"distribution": dist, "min": p.low, "max": p.high}
    return params


class WandbRunner:
    """SweepRunner that delegates trial execution to the wandb sweep agent.

    Converts the :class:`SearchSpace` to a wandb sweep configuration, creates
    the sweep via ``wandb.sweep``, and runs the agent via ``wandb.agent``.
    Requires the ``tracking-wandb`` optional extra.
    """

    def __init__(
        self,
        search_space: SearchSpace,
        config: SweepsConfig,
        base_overrides: list[str] | None = None,
        project: str | None = None,
    ) -> None:
        """Initialise the runner.

        Args:
            search_space: Hyperparameter search space to sweep over.
            config: Sweep configuration controlling backend semantics.
            base_overrides: Hydra overrides applied to each bootstrapped trial context.
            project: wandb project name.  When ``None``, the active wandb
                project is used.
        """
        self._space = search_space
        self._config = config
        self._base_overrides = list(base_overrides or [])
        self._project = project

    def _build_sweep_config(self) -> dict[str, Any]:
        """Build the wandb sweep configuration from starter semantics."""
        method = "grid" if self._config.strategy == "grid" else "random"
        return {
            "method": method,
            "parameters": _to_wandb_config(self._space),
        }

    def run(
        self,
        override_sets: list[list[str]],
        trial_fn: TrialFn,
    ) -> SweepSummary:
        """Create a wandb sweep and run the agent until all trials complete.

        Args:
            override_sets: Override sets generated from the search space
                (used for result bookkeeping only; wandb controls sampling).
            trial_fn: Callable with signature
                ``(RuntimeContext, Mapping[str, Any]) -> dict[str, float]``.

        Returns:
            :class:`SweepSummary` containing one :class:`SweepResult` per
            completed agent call.

        Raises:
            ImportError: If ``wandb`` is not installed.
        """
        try:
            wandb: Any = import_module("wandb")
        except ImportError as exc:
            raise ImportError(
                "wandb is not installed. Install starter with the 'tracking-wandb' extra: "
                "pip install 'starter[tracking-wandb]'"
            ) from exc

        sweep_config = self._build_sweep_config()
        sweep_id = wandb.sweep(sweep_config, project=self._project)

        results: list[SweepResult] = []

        def _agent_fn() -> None:
            from starter.runtime import bootstrap

            run = wandb.init()
            overrides = [f"{k}={v}" for k, v in run.config.items()]
            params = dict(run.config.items())
            try:
                with bootstrap(self._base_overrides) as ctx:
                    metrics = trial_fn(ctx, params)
                    wandb.log(metrics)
                results.append(
                    SweepResult(
                        trial_index=len(results),
                        override_set=overrides,
                        status="success",
                        metrics=metrics,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                results.append(
                    SweepResult(
                        trial_index=len(results),
                        override_set=overrides,
                        status="failed",
                        error=str(exc),
                    )
                )
            finally:
                wandb.finish()

        count = self._config.n_trials if self._config.strategy == "random" else len(override_sets)
        wandb.agent(sweep_id, function=_agent_fn, count=count)
        return SweepSummary(results=results)
