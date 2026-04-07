"""OmegaConf custom resolvers for the starter config subsystem."""

from __future__ import annotations

import os
from pathlib import Path

from omegaconf import OmegaConf


def _workspace_root() -> str:
    """Return the workspace root path.

    Reads ``STARTER_WORKSPACE_ROOT`` when set; falls back to the current
    working directory.

    Returns:
        Absolute path string for the workspace root.
    """
    candidate = os.environ.get("STARTER_WORKSPACE_ROOT")
    if candidate:
        return str(Path(candidate).expanduser().resolve())
    return str(Path.cwd().resolve())


def register_resolvers() -> None:
    """Register the ``path_guard`` OmegaConf resolver.

    The resolver accepts a single key argument:

    - ``repo_root`` — resolves to the workspace root path.

    Registered with ``replace=True`` to allow repeated calls without error.
    """

    def _resolve(key: str) -> str:
        if key == "repo_root":
            return _workspace_root()
        return ""

    OmegaConf.register_new_resolver("path_guard", _resolve, replace=True)
