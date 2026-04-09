"""Typed dataclass schema for the starter application config."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from omegaconf import MISSING


@dataclass
class AppSection:
    """Application identity metadata."""

    name: str = "starter"
    subsystem: str = "config"
    version: str = "0.1.2"


@dataclass
class EnvSection:
    """Execution environment descriptor."""

    workspace: str = MISSING
    name: str = "local"
    platform: str = "local"


@dataclass
class PathsSection:
    """Shared filesystem path conventions."""

    repo_root: str = MISSING
    config_root: str = MISSING
    output_dir: str = MISSING
    artifacts_dir: str = MISSING
    cache_dir: str = MISSING


@dataclass
class RuntimeSection:
    """Execution-mode flags and global settings."""

    debug: bool = False
    seed: int = 7
    strict_config: bool = True
    profile: str = "default"


@dataclass
class AppConfig:
    """Top-level typed configuration schema for the starter library.

    Subsystem sections (``logging``, ``tracking``, ``profiling``,
    ``artifacts``, ``sweeps``) are stored as plain dicts and passed directly
    to the corresponding subsystem factory.  Detailed schema ownership remains
    with each subsystem.
    """

    app: AppSection = field(default_factory=AppSection)
    env: EnvSection = field(default_factory=EnvSection)
    paths: PathsSection = field(default_factory=PathsSection)
    runtime: RuntimeSection = field(default_factory=RuntimeSection)
    logging: dict[str, Any] = field(default_factory=dict)
    tracking: dict[str, Any] = field(default_factory=dict)
    profiling: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    sweeps: dict[str, Any] = field(default_factory=dict)
