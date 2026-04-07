import os
import subprocess
import sys
from pathlib import Path

from starter.config import compose_typed_config
from starter.tracking import NullTracker, build_tracker, parse_tracking_config
from starter.tracking.backends.wandb import WandbTracker
from starter.tracking.core.schema import TrackingConfig, WandbTrackingConfig
from starter.tracking.core.validate import validate_tracking_config


def test_config_compose_includes_tracking_section() -> None:
    cfg = compose_typed_config()

    assert cfg.tracking["backend"] == "disabled"
    assert cfg.tracking["enabled"] is False


def test_build_disabled_tracker_returns_null_tracker() -> None:
    cfg = compose_typed_config(["tracking=disabled"])
    tracker = build_tracker(cfg.tracking)

    assert isinstance(tracker, NullTracker)


def test_wandb_tracking_requires_api_key_for_online_mode() -> None:
    cfg = TrackingConfig(
        backend="wandb",
        enabled=True,
        wandb=WandbTrackingConfig(
            project="starter",
            entity=None,
            api_key=None,
            mode="online",
            tags=[],
        ),
    )

    try:
        validate_tracking_config(cfg)
    except ValueError as exc:
        assert "WANDB_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected WandB tracking validation to fail without an API key.")


def test_wandb_tracking_accepts_offline_mode_without_api_key() -> None:
    cfg = parse_tracking_config(
        {
            "backend": "wandb",
            "enabled": True,
            "run_name": "offline-run",
            "wandb": {
                "project": "starter",
                "entity": None,
                "api_key": None,
                "mode": "offline",
                "tags": ["baseline"],
                "group": "offline-group",
                "job_type": "smoke",
                "notes": "offline",
            },
        }
    )

    assert cfg.wandb.mode == "offline"
    assert cfg.run_name == "offline-run"
    assert cfg.wandb.group == "offline-group"


def test_build_wandb_tracker_returns_backend_instance() -> None:
    tracker = build_tracker(
        {
            "backend": "wandb",
            "enabled": True,
            "run_name": "demo",
            "wandb": {
                "project": "starter",
                "entity": None,
                "api_key": "key",
                "mode": "offline",
                "tags": [],
                "group": None,
                "job_type": None,
                "notes": None,
            },
        }
    )

    assert isinstance(tracker, WandbTracker)


def test_wandb_tracker_raises_clear_error_when_dependency_is_missing() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from starter.tracking import build_tracker; "
                "tracker = build_tracker({"
                "'backend': 'wandb', 'enabled': True, "
                "'wandb': {'project': 'starter', 'mode': 'offline', 'tags': [], "
                "'entity': None, 'api_key': None, 'group': None, 'job_type': None, 'notes': None}"
                "}); "
                "tracker.start_run()"
            ),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert completed.returncode != 0
    assert "tracking-wandb" in completed.stderr or "tracking-wandb" in completed.stdout
