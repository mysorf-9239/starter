"""Validation functions for TrackingConfig."""

from __future__ import annotations

from .schema import TrackingConfig

_VALID_BACKENDS = {"disabled", "wandb"}
_VALID_WANDB_MODES = {"disabled", "offline", "online"}


def validate_tracking_config(cfg: TrackingConfig) -> None:
    """Validate a :class:`TrackingConfig` instance.

    Args:
        cfg: Tracking configuration to validate.

    Raises:
        ValueError: If any constraint is violated.
    """
    if cfg.backend not in _VALID_BACKENDS:
        raise ValueError("tracking.backend must be one of: disabled, wandb.")
    if cfg.backend == "disabled" and cfg.enabled:
        raise ValueError("tracking.enabled must be false when backend is disabled.")
    if cfg.backend != "wandb" or not cfg.enabled:
        return
    if not cfg.wandb.project:
        raise ValueError("tracking.wandb.project is required when WandB tracking is enabled.")
    if cfg.wandb.mode not in _VALID_WANDB_MODES:
        raise ValueError("tracking.wandb.mode must be one of: disabled, offline, online.")
    if cfg.wandb.mode == "online" and not cfg.wandb.api_key:
        raise ValueError("WANDB_API_KEY is required when WandB tracking runs in online mode.")
