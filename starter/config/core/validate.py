"""Validation functions for composed AppConfig instances."""

from __future__ import annotations

from pathlib import Path

from omegaconf import DictConfig, OmegaConf

from starter.tracking.core.schema import TrackingConfig
from starter.tracking.core.validate import validate_tracking_config

from .schema import AppConfig


def validate_paths(cfg: AppConfig) -> None:
    """Validate path invariants defined in the shared starter layout.

    ``paths.repo_root`` existence is not enforced: when installed as a library,
    the resolver returns the caller's working directory, which may differ from
    the original source tree.

    Args:
        cfg: Typed application config.

    Raises:
        ValueError: If any path field is not absolute.
    """
    repo_root = Path(cfg.paths.repo_root)
    if not repo_root.is_absolute():
        raise ValueError("paths.repo_root must be an absolute path.")

    config_root = Path(cfg.paths.config_root)
    if not config_root.is_absolute():
        raise ValueError("paths.config_root must be an absolute path.")

    for name in ("output_dir", "artifacts_dir", "cache_dir"):
        path_value = Path(getattr(cfg.paths, name))
        if not path_value.is_absolute():
            raise ValueError(f"paths.{name} must be an absolute path.")


def validate_runtime(cfg: AppConfig) -> None:
    """Validate runtime section semantics.

    Args:
        cfg: Typed application config.

    Raises:
        ValueError: If ``runtime.seed`` is negative or ``runtime.profile`` is
            empty.
    """
    if cfg.runtime.seed < 0:
        raise ValueError("runtime.seed must be >= 0.")
    if not cfg.runtime.profile:
        raise ValueError("runtime.profile must be non-empty.")


def validate_tracking(cfg: AppConfig) -> None:
    """Delegate tracking section validation to the tracking subsystem.

    Args:
        cfg: Typed application config.

    Raises:
        ValueError: If the tracking configuration is invalid.
    """
    tracking_cfg = OmegaConf.to_object(
        OmegaConf.merge(OmegaConf.structured(TrackingConfig), OmegaConf.create(cfg.tracking))
    )
    if not isinstance(tracking_cfg, TrackingConfig):
        raise ValueError("Expected typed TrackingConfig during tracking validation.")
    validate_tracking_config(tracking_cfg)


def validate_config(cfg: AppConfig) -> None:
    """Run all cross-section validations on a typed AppConfig.

    Args:
        cfg: Typed application config.

    Raises:
        ValueError: If any validation rule is violated.
    """
    validate_paths(cfg)
    validate_runtime(cfg)
    validate_tracking(cfg)


def validate_dict_config(cfg: DictConfig) -> None:
    """Validate a raw DictConfig by merging it into the typed schema.

    Args:
        cfg: Hydra-composed DictConfig to validate.

    Raises:
        ValueError: If the config cannot be merged into AppConfig or fails
            validation.
    """
    structured = OmegaConf.structured(AppConfig)
    merged = OmegaConf.merge(structured, cfg)
    OmegaConf.resolve(merged)
    typed = OmegaConf.to_object(merged)
    if not isinstance(typed, AppConfig):
        raise ValueError("Expected a typed AppConfig after structured merge.")
    validate_config(typed)
