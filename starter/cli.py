"""Hydra CLI entrypoint for the starter config subsystem."""

from __future__ import annotations

import hydra
from omegaconf import DictConfig

from .config.core.compose import redact_secrets
from .config.core.resolvers import register_resolvers
from .config.core.validate import validate_dict_config

register_resolvers()


@hydra.main(version_base=None, config_path="../conf", config_name="config")
def main(cfg: DictConfig) -> None:
    """Compose, validate, and print the current configuration."""
    validate_dict_config(cfg)
    print(redact_secrets(cfg))


if __name__ == "__main__":
    main()
