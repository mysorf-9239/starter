"""Hydra config composition API for the starter config subsystem."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from hydra import compose, initialize_config_dir
from omegaconf import DictConfig, OmegaConf

from .registry import register_config_store
from .resolvers import register_resolvers
from .schema import AppConfig
from .validate import validate_config


def _config_dir() -> str:
    """Resolve the active ``conf/`` directory.

    Resolution order:

    1. ``STARTER_CONFIG_DIR`` environment variable — explicit override.
    2. Bundled ``conf/`` inside the installed package at
       ``<site-packages>/starter/conf/``.
    3. Repository root ``conf/`` — three levels above this file, used during
       development and editable installs.

    Returns:
        Absolute path to the resolved ``conf/`` directory.
    """
    env_override = os.environ.get("STARTER_CONFIG_DIR")
    if env_override:
        return str(Path(env_override).expanduser().resolve())

    installed = Path(__file__).resolve().parents[2] / "conf"
    if installed.is_dir():
        return str(installed)

    return str(Path(__file__).resolve().parents[3] / "conf")


def compose_config(
    overrides: Sequence[str] | None = None,
    *,
    config_name: str = "config",
) -> DictConfig:
    """Compose a raw :class:`DictConfig` from the Hydra config groups.

    Args:
        overrides: Hydra override strings, e.g. ``["logging=rich"]``.
        config_name: Name of the root config file (without ``.yaml``).

    Returns:
        Composed :class:`DictConfig`.
    """
    register_resolvers()
    register_config_store()
    with initialize_config_dir(version_base=None, config_dir=_config_dir()):
        cfg = compose(config_name=config_name, overrides=list(overrides or []))
    return cfg


def compose_typed_config(
    overrides: Sequence[str] | None = None,
    *,
    config_name: str = "config",
    resolve: bool = True,
    validate: bool = True,
) -> AppConfig:
    """Compose and merge the Hydra config into the typed :class:`AppConfig` schema.

    Args:
        overrides: Hydra override strings.
        config_name: Name of the root config file (without ``.yaml``).
        resolve: When ``True``, OmegaConf interpolations are resolved before
            conversion.
        validate: When ``True``, :func:`~starter.config.validate_config` is
            called on the resulting object.

    Returns:
        Typed :class:`AppConfig` instance.

    Raises:
        ValueError: If *validate* is ``True`` and the config fails validation.
    """
    structured = OmegaConf.structured(AppConfig)
    raw = compose_config(overrides=overrides, config_name=config_name)
    merged = OmegaConf.merge(structured, raw)
    if resolve:
        OmegaConf.resolve(merged)
    typed = cast(AppConfig, OmegaConf.to_object(merged))
    if validate:
        validate_config(typed)
    return typed


def to_yaml(overrides: Sequence[str] | None = None, *, resolve: bool = False) -> str:
    """Render the composed config as a YAML string.

    Args:
        overrides: Hydra override strings.
        resolve: When ``True``, OmegaConf interpolations are resolved before
            rendering.

    Returns:
        YAML representation of the composed config.
    """
    return OmegaConf.to_yaml(compose_config(overrides=overrides), resolve=resolve)


def redact_secrets(cfg: DictConfig | AppConfig) -> str:
    """Render the config as YAML with known secret values replaced by a mask.

    Currently masked paths:

    - ``tracking.wandb.api_key``

    Args:
        cfg: Composed config as either a :class:`DictConfig` or a typed
            :class:`AppConfig`.

    Returns:
        YAML string with secret values replaced by ``***REDACTED***``.
    """
    if isinstance(cfg, DictConfig):
        data = OmegaConf.to_container(cfg, resolve=True)
    else:
        data = OmegaConf.to_container(OmegaConf.structured(cfg), resolve=True)

    if isinstance(data, dict):
        tracking = data.get("tracking")
        if isinstance(tracking, dict):
            wandb = tracking.get("wandb")
            if isinstance(wandb, dict) and wandb.get("api_key"):
                wandb["api_key"] = "***REDACTED***"
    return OmegaConf.to_yaml(data, resolve=True)
