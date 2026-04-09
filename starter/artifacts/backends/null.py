"""No-op ArtifactManager implementation for the disabled backend."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..core.schema import ArtifactRecord, ArtifactType


class NullArtifactManager:
    """No-op ArtifactManager that produces no filesystem side effects.

    All methods conform to the :class:`ArtifactManager` protocol.
    ``save`` returns a valid :class:`ArtifactRecord` with a synthetic path;
    ``load`` returns the expected path without checking the filesystem;
    ``list_artifacts`` always returns an empty list; ``delete`` is a no-op.
    """

    def save(
        self,
        source: Path | str,
        name: str,
        artifact_type: ArtifactType,
        version: str | None = None,
    ) -> ArtifactRecord:
        resolved_version = version or "null"
        path = Path(artifact_type.value) / name / resolved_version / Path(source).name
        return ArtifactRecord(
            name=name,
            version=resolved_version,
            path=path,
            artifact_type=artifact_type,
            size_bytes=0,
            created_at=datetime.now(timezone.utc),
        )

    def load(
        self,
        name: str,
        artifact_type: ArtifactType,
        version: str | None = None,
    ) -> Path:
        resolved_version = version or "null"
        return Path(artifact_type.value) / name / resolved_version

    def resolve_path(
        self,
        name: str,
        artifact_type: ArtifactType,
        version: str,
    ) -> Path:
        return Path(artifact_type.value) / name / version

    def list_artifacts(
        self,
        artifact_type: ArtifactType | None = None,
        name: str | None = None,
    ) -> list[ArtifactRecord]:
        return []

    def delete(
        self,
        name: str,
        artifact_type: ArtifactType,
        version: str,
    ) -> None:
        pass
