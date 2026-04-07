"""Schema and data models for the artifacts subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class ArtifactType(str, Enum):
    """Classification of artifact kinds."""

    CHECKPOINT = "checkpoint"
    DATASET = "dataset"
    OUTPUT = "output"
    GENERIC = "generic"


class VersioningStrategy(str, Enum):
    """Strategy for auto-generating artifact versions."""

    RUN_ID = "run_id"
    EPOCH = "epoch"
    TIMESTAMP = "timestamp"
    MANUAL = "manual"


@dataclass
class ArtifactsConfig:
    """Configuration schema owned by the artifacts subsystem."""

    backend: str = "local"
    enabled: bool = True
    base_dir: str | None = None
    versioning_strategy: str = "run_id"


@dataclass
class ArtifactRecord:
    """Metadata describing a saved artifact."""

    name: str
    version: str
    path: Path
    artifact_type: ArtifactType
    size_bytes: int
    created_at: datetime = field(default_factory=datetime.utcnow)
