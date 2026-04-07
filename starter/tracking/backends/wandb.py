"""Weights & Biases tracking backend."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from ..core.schema import TrackingConfig


class WandbTracker:
    """Thin adapter over the W&B SDK."""

    def __init__(self, cfg: TrackingConfig) -> None:
        self._cfg = cfg
        self._run: Any = None
        self._wandb_module: Any = None

    def _import_wandb(self) -> Any:
        try:
            import wandb
        except ImportError as exc:
            raise RuntimeError(
                "wandb is not installed. Install starter with the 'tracking-wandb' extra."
            ) from exc
        self._wandb_module = wandb
        return wandb

    def start_run(self, *, run_name: str | None = None) -> None:
        wandb = self._import_wandb()
        if self._cfg.wandb.api_key:
            os.environ.setdefault("WANDB_API_KEY", self._cfg.wandb.api_key)

        self._run = wandb.init(
            project=self._cfg.wandb.project,
            entity=self._cfg.wandb.entity,
            name=run_name or self._cfg.run_name,
            mode=self._cfg.wandb.mode,
            tags=list(self._cfg.wandb.tags),
            group=self._cfg.wandb.group,
            job_type=self._cfg.wandb.job_type,
            notes=self._cfg.wandb.notes,
        )

    def log_params(self, params: Mapping[str, Any]) -> None:
        if self._run is None:
            self.start_run()
        if self._run is None:
            raise RuntimeError("Failed to start wandb run.")
        self._run.config.update(dict(params), allow_val_change=True)

    def log_metrics(self, metrics: Mapping[str, float], *, step: int | None = None) -> None:
        if self._run is None:
            self.start_run()
        if self._run is None:
            raise RuntimeError("Failed to start wandb run.")
        payload = dict(metrics)
        if step is None:
            self._run.log(payload)
        else:
            self._run.log(payload, step=step)

    def log_artifact(self, path: str, *, name: str | None = None) -> None:
        if self._run is None:
            self.start_run()
        if self._run is None:
            raise RuntimeError("Failed to start wandb run.")
        wandb = self._wandb_module or self._import_wandb()

        artifact = wandb.Artifact(name or "artifact", type="artifact")
        artifact.add_file(path)
        self._run.log_artifact(artifact)

    def finish(self) -> None:
        if self._run is not None:
            self._run.finish()
            self._run = None
