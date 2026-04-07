"""Exceptions for the artifacts subsystem."""

from __future__ import annotations


class ArtifactNotFoundError(Exception):
    """Raised when an artifact cannot be found in storage."""
