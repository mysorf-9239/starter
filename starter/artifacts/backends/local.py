"""Local filesystem implementation of the ArtifactManager protocol."""

from __future__ import annotations

import logging
import shutil
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from ..core.exceptions import ArtifactNotFoundError
from ..core.schema import ArtifactRecord, ArtifactType, VersioningStrategy

if TYPE_CHECKING:
    from starter.tracking.core.interfaces import Tracker

logger = logging.getLogger(__name__)


def _dir_size(path: Path) -> int:
    """Return the total size in bytes of all files under *path*, recursively.

    Args:
        path: Root directory to measure.

    Returns:
        Total byte count of all regular files beneath *path*.
    """
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _cleanup_path(path: Path) -> None:
    """Remove a file or directory best-effort."""
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
        return
    with suppress(FileNotFoundError):
        path.unlink()


class LocalBackend:
    """ArtifactManager backed by the local filesystem.

    Artifacts are stored under a structured path::

        {base_dir}/{artifact_type}/{name}/{version}/{filename}

    Version strings are derived from the configured :class:`VersioningStrategy`.
    An optional :class:`Tracker` receives a ``log_artifact`` call after each
    successful save; failures are logged as warnings and do not interrupt the
    save operation.
    """

    def __init__(
        self,
        base_dir: str,
        versioning_strategy: str = "run_id",
        run_id: str | None = None,
        tracker: Tracker | None = None,
    ) -> None:
        """Initialise the backend.

        Args:
            base_dir: Root directory for artifact storage.
            versioning_strategy: One of ``"run_id"``, ``"epoch"``,
                ``"timestamp"``, or ``"manual"``.
            run_id: Identifier used when *versioning_strategy* is ``"run_id"``.
            tracker: Optional tracker that receives artifact upload calls.
        """
        self._base_dir = Path(base_dir)
        self._strategy = VersioningStrategy(versioning_strategy)
        self._run_id = run_id
        self._tracker = tracker

    def _resolve_version(self, version: str | None) -> str:
        """Derive the effective version string from the configured strategy.

        Args:
            version: Caller-supplied version override, or ``None`` to use the
                strategy default.

        Returns:
            The resolved version string.

        Raises:
            ValueError: If the strategy requires a value that is absent.
        """
        if self._strategy == VersioningStrategy.RUN_ID:
            if version is not None:
                return version
            if self._run_id is None:
                raise ValueError(
                    "versioning_strategy=RUN_ID requires run_id to be set on the manager."
                )
            return self._run_id

        if self._strategy == VersioningStrategy.EPOCH:
            if version is None:
                raise ValueError(
                    "versioning_strategy=EPOCH requires an explicit version (epoch number)."
                )
            try:
                epoch_int = int(version)
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"versioning_strategy=EPOCH expects an integer version, got {version!r}."
                ) from exc
            return f"epoch_{epoch_int:04d}"

        if self._strategy == VersioningStrategy.TIMESTAMP:
            if version is not None:
                return version
            return datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")

        # VersioningStrategy.MANUAL
        if version is None:
            raise ValueError("versioning_strategy=MANUAL requires an explicit version string.")
        return version

    def resolve_path(
        self,
        name: str,
        artifact_type: ArtifactType,
        version: str,
    ) -> Path:
        """Return the canonical destination path for an artifact without side effects.

        Args:
            name: Artifact name.
            artifact_type: Classification of the artifact.
            version: Version string.

        Returns:
            Absolute :class:`Path` to the artifact directory.
        """
        return self._base_dir / artifact_type.value / name / version

    def save(
        self,
        source: Path | str,
        name: str,
        artifact_type: ArtifactType,
        version: str | None = None,
    ) -> ArtifactRecord:
        """Copy *source* into managed storage and return its metadata record.

        Args:
            source: Path to the file or directory to store.
            name: Logical name for the artifact.
            artifact_type: Classification of the artifact.
            version: Explicit version string; derived from the strategy when
                ``None``.

        Returns:
            An :class:`ArtifactRecord` describing the stored artifact.

        Raises:
            ArtifactNotFoundError: If *source* does not exist.
            ValueError: If the versioning strategy requires a value that is
                absent.
        """
        src = Path(source)
        if not src.exists():
            raise ArtifactNotFoundError(f"Source path does not exist: {src}")

        resolved_version = self._resolve_version(version)
        dest_dir = self.resolve_path(name, artifact_type, resolved_version)
        version_root = dest_dir.parent
        version_root.mkdir(parents=True, exist_ok=True)

        staged_dir = version_root / f".tmp-{resolved_version}-{uuid4().hex}"
        staged_dest = staged_dir / src.name
        final_dest = dest_dir / src.name

        try:
            staged_dir.mkdir(parents=True, exist_ok=False)
            if src.is_dir():
                shutil.copytree(src, staged_dest)
                size = _dir_size(staged_dest)
            else:
                shutil.copy2(src, staged_dest)
                size = staged_dest.stat().st_size

            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            staged_dir.replace(dest_dir)
        except Exception:
            _cleanup_path(staged_dir)
            raise

        record = ArtifactRecord(
            name=name,
            version=resolved_version,
            path=final_dest,
            artifact_type=artifact_type,
            size_bytes=size,
            created_at=datetime.now(timezone.utc),
        )

        if self._tracker is not None:
            try:
                self._tracker.log_artifact(str(record.path), name=record.name)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "tracker.log_artifact() failed after saving artifact %r: %s", name, exc
                )

        return record

    def load(
        self,
        name: str,
        artifact_type: ArtifactType,
        version: str | None = None,
    ) -> Path:
        """Return the path to a stored artifact.

        Args:
            name: Artifact name.
            artifact_type: Classification of the artifact.
            version: Specific version to load.  When ``None``, the latest
                version is selected by lexicographic descending order.

        Returns:
            :class:`Path` to the artifact directory.

        Raises:
            ArtifactNotFoundError: If no matching artifact exists.
        """
        type_dir = self._base_dir / artifact_type.value / name

        if version is not None:
            dest_dir = type_dir / version
            if not dest_dir.exists():
                raise ArtifactNotFoundError(
                    f"Artifact not found: name={name!r}, type={artifact_type.value!r}, "
                    f"version={version!r}"
                )
            return dest_dir

        if not type_dir.exists():
            raise ArtifactNotFoundError(
                f"No artifacts found for name={name!r}, type={artifact_type.value!r}"
            )
        versions = sorted(
            [d.name for d in type_dir.iterdir() if d.is_dir()],
            reverse=True,
        )
        if not versions:
            raise ArtifactNotFoundError(
                f"No versions found for name={name!r}, type={artifact_type.value!r}"
            )
        return type_dir / versions[0]

    def list_artifacts(
        self,
        artifact_type: ArtifactType | None = None,
        name: str | None = None,
    ) -> list[ArtifactRecord]:
        """Return all stored artifact records, optionally filtered.

        Args:
            artifact_type: When provided, restrict results to this type.
            name: When provided, restrict results to this artifact name.

        Returns:
            List of :class:`ArtifactRecord` instances sorted by
            ``created_at`` ascending.  Returns an empty list when
            ``base_dir`` does not exist.
        """
        if not self._base_dir.exists():
            return []

        records: list[ArtifactRecord] = []
        type_dirs = (
            [self._base_dir / artifact_type.value]
            if artifact_type is not None
            else [d for d in self._base_dir.iterdir() if d.is_dir()]
        )

        for type_dir in type_dirs:
            if not type_dir.exists():
                continue
            try:
                at = ArtifactType(type_dir.name)
            except ValueError:
                continue

            name_dirs = [type_dir / name] if name is not None else list(type_dir.iterdir())
            for name_dir in name_dirs:
                if not name_dir.is_dir():
                    continue
                for version_dir in name_dir.iterdir():
                    if not version_dir.is_dir():
                        continue
                    children = list(version_dir.iterdir())
                    if not children:
                        continue
                    artifact_path = children[0]
                    stat = artifact_path.stat()
                    size = _dir_size(artifact_path) if artifact_path.is_dir() else stat.st_size
                    records.append(
                        ArtifactRecord(
                            name=name_dir.name,
                            version=version_dir.name,
                            path=artifact_path,
                            artifact_type=at,
                            size_bytes=size,
                            created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                        )
                    )

        records.sort(key=lambda r: r.created_at)
        return records

    def delete(
        self,
        name: str,
        artifact_type: ArtifactType,
        version: str,
    ) -> None:
        """Remove a stored artifact from the filesystem.

        Args:
            name: Artifact name.
            artifact_type: Classification of the artifact.
            version: Version to delete.

        Raises:
            ArtifactNotFoundError: If the specified artifact does not exist.
        """
        dest_dir = self.resolve_path(name, artifact_type, version)
        if not dest_dir.exists():
            raise ArtifactNotFoundError(
                f"Artifact not found: name={name!r}, type={artifact_type.value!r}, "
                f"version={version!r}"
            )
        shutil.rmtree(dest_dir)
