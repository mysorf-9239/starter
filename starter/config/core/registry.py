"""Hydra ConfigStore registration for the starter config schema."""

from __future__ import annotations

from hydra.core.config_store import ConfigStore

from .schema import AppConfig


def register_config_store() -> None:
    """Register the top-level schema for typed composition."""
    cs = ConfigStore.instance()
    cs.store(name="starter_schema", node=AppConfig)
