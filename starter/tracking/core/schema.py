"""Schema owned by the tracking subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WandbTrackingConfig:
    project: str | None = None
    entity: str | None = None
    api_key: str | None = None
    mode: str = "disabled"
    tags: list[str] = field(default_factory=list)
    group: str | None = None
    job_type: str | None = None
    notes: str | None = None


@dataclass
class TrackingConfig:
    backend: str = "disabled"
    enabled: bool = False
    run_name: str | None = None
    save_config: bool = True
    wandb: WandbTrackingConfig = field(default_factory=WandbTrackingConfig)
