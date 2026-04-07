"""Validation functions for SweepsConfig."""

from __future__ import annotations

from .schema import SweepsConfig

_SUPPORTED_BACKENDS = {"local", "wandb"}
_SUPPORTED_STRATEGIES = {"grid", "random"}


def validate_sweeps_config(cfg: SweepsConfig) -> None:
    """Validate a :class:`SweepsConfig` instance.

    Args:
        cfg: Sweeps configuration to validate.

    Raises:
        ValueError: If any constraint is violated.
    """
    if cfg.backend not in _SUPPORTED_BACKENDS:
        raise ValueError(
            f"Unsupported sweeps backend: {cfg.backend!r}. "
            f"Valid options: {sorted(_SUPPORTED_BACKENDS)}"
        )
    if cfg.strategy not in _SUPPORTED_STRATEGIES:
        raise ValueError(
            f"Unsupported sweeps strategy: {cfg.strategy!r}. "
            f"Valid options: {sorted(_SUPPORTED_STRATEGIES)}"
        )
    if cfg.strategy == "random" and cfg.n_trials is None:
        raise ValueError("n_trials is required when strategy is 'random'.")
