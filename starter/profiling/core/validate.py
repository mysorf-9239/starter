"""Validation functions for ProfilingConfig."""

from __future__ import annotations

from .schema import ProfilingConfig

_VALID_BACKENDS = {"disabled", "basic", "pandas"}


def validate_profiling_config(cfg: ProfilingConfig) -> None:
    """Validate a :class:`ProfilingConfig` instance.

    Args:
        cfg: Profiling configuration to validate.

    Raises:
        ValueError: If any constraint is violated.
    """
    if cfg.backend not in _VALID_BACKENDS:
        raise ValueError("profiling.backend must be one of: disabled, basic, pandas.")
    if cfg.backend == "disabled" and cfg.enabled:
        raise ValueError("profiling.enabled must be false when backend is disabled.")
    if cfg.top_k <= 0:
        raise ValueError("profiling.top_k must be > 0.")
    if cfg.sample_size is not None and cfg.sample_size <= 0:
        raise ValueError("profiling.sample_size must be > 0 when provided.")
