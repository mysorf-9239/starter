"""Interfaces for the artifacts subsystem."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .schema import ArtifactRecord, ArtifactType


class ArtifactManager(Protocol):
    """Minimal artifact manager interface for ML/research workflows."""

    def save(
        self,
        source: Path | str,
        name: str,
        artifact_type: ArtifactType,
        version: str | None = None,
    ) -> ArtifactRecord: ...

    def load(
        self,
        name: str,
        artifact_type: ArtifactType,
        version: str | None = None,
    ) -> Path: ...

    def resolve_path(
        self,
        name: str,
        artifact_type: ArtifactType,
        version: str,
    ) -> Path: ...

    def list_artifacts(
        self,
        artifact_type: ArtifactType | None = None,
        name: str | None = None,
    ) -> list[ArtifactRecord]: ...

    def delete(
        self,
        name: str,
        artifact_type: ArtifactType,
        version: str,
    ) -> None: ...
