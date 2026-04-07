"""Factory functions for constructing Tracker instances from config."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from omegaconf import DictConfig, OmegaConf

from ..backends.null import NullTracker
from ..backends.wandb import WandbTracker
from .interfaces import Tracker
from .schema import TrackingConfig
from .validate import validate_tracking_config


def parse_tracking_config(data: Mapping[str, Any] | DictConfig | TrackingConfig) -> TrackingConfig:
    """Parse and validate an external config mapping into a :class:`TrackingConfig`.

    Args:
        data: Raw config as a :class:`Mapping`, :class:`DictConfig`, or an
            already-typed :class:`TrackingConfig`.

    Returns:
        Validated :class:`TrackingConfig` instance.

    Raises:
        ValueError: If the config fails validation.
    """
    if isinstance(data, TrackingConfig):
        cfg = data
    elif isinstance(data, DictConfig):
        cfg = cast(
            TrackingConfig,
            OmegaConf.to_object(OmegaConf.merge(OmegaConf.structured(TrackingConfig), data)),
        )
    else:
        cfg = cast(
            TrackingConfig,
            OmegaConf.to_object(OmegaConf.merge(OmegaConf.structured(TrackingConfig), dict(data))),
        )
    validate_tracking_config(cfg)
    return cfg


def build_tracker(data: Mapping[str, Any] | DictConfig | TrackingConfig) -> Tracker:
    """Construct a :class:`Tracker` from a config section.

    Args:
        data: Tracking config as a :class:`Mapping`, :class:`DictConfig`, or
            :class:`TrackingConfig`.

    Returns:
        A :class:`Tracker` instance for the configured backend, or a
        :class:`NullTracker` when the backend is ``"disabled"`` or
        ``enabled`` is ``False``.

    Raises:
        ValueError: If the backend identifier is not supported.
    """
    cfg = parse_tracking_config(data)
    if cfg.backend == "disabled" or not cfg.enabled:
        return NullTracker()
    if cfg.backend == "wandb":
        return WandbTracker(cfg)
    raise ValueError(f"Unsupported tracking backend: {cfg.backend}")
