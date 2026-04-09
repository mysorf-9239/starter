"""Hydra config composition API for the starter config subsystem."""

from __future__ import annotations

import os
from collections.abc import Sequence
from importlib import import_module
from pathlib import Path
from typing import cast

from hydra import compose, initialize_config_dir
from hydra.core.global_hydra import GlobalHydra
from omegaconf import DictConfig, OmegaConf

from .registry import register_config_store
from .resolvers import register_resolvers
from .schema import AppConfig
from .validate import validate_config


def _config_dir() -> str:
    """Resolve the active ``conf/`` directory.

    Resolution order:

    1. ``STARTER_CONFIG_DIR`` environment variable — explicit override.
    2. Repository root ``conf/`` — three levels above this file, used during
       development and editable installs.
    3. Bundled ``conf/`` inside the installed package at
       ``<site-packages>/starter/conf/``.

    Returns:
        Absolute path to the resolved ``conf/`` directory.
    """
    env_override = os.environ.get("STARTER_CONFIG_DIR")
    if env_override:
        return str(Path(env_override).expanduser().resolve())

    repo_conf = Path(__file__).resolve().parents[3] / "conf"
    if repo_conf.is_dir():
        return str(repo_conf)

    installed_conf = Path(__file__).resolve().parents[2] / "conf"
    if installed_conf.is_dir():
        return str(installed_conf)

    raise FileNotFoundError("Unable to resolve a starter conf/ directory.")


def _parse_simple_env_file(path: Path) -> dict[str, str]:
    """Parse a simple ``.env`` file without external dependencies."""
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        if key:
            values[key] = value
    return values


def _read_env_file(path: Path) -> dict[str, str]:
    """Read environment values from *path*."""
    try:
        dotenv_values = import_module("dotenv").dotenv_values
    except ImportError:
        return _parse_simple_env_file(path)

    data = dotenv_values(path)
    return {str(key): str(value) for key, value in data.items() if key and value is not None}


def _candidate_env_files() -> list[Path]:
    """Return discovered ``.env`` candidates in precedence order."""
    candidates: list[Path] = []

    explicit_env = os.environ.get("STARTER_ENV_FILE")
    if explicit_env:
        candidates.append(Path(explicit_env).expanduser().resolve())

    workspace_root = os.environ.get("STARTER_WORKSPACE_ROOT")
    if workspace_root:
        candidates.append(Path(workspace_root).expanduser().resolve() / ".env")

    candidates.append(Path.cwd().resolve() / ".env")

    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)
    return unique


def load_env_files() -> list[Path]:
    """Load discovered ``.env`` files into ``os.environ`` without overwriting OS env.

    Resolution order:

    1. ``STARTER_ENV_FILE``
    2. ``STARTER_WORKSPACE_ROOT/.env``
    3. ``cwd/.env``

    Returns:
        List of env files that were found and loaded.
    """
    loaded: list[Path] = []
    for candidate in _candidate_env_files():
        if not candidate.is_file():
            continue
        for key, value in _read_env_file(candidate).items():
            os.environ.setdefault(key, value)
        loaded.append(candidate)
    return loaded


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
    load_env_files()
    register_resolvers()
    register_config_store()
    global_hydra = GlobalHydra.instance()
    if global_hydra.is_initialized():
        global_hydra.clear()
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
