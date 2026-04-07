import os
import subprocess
import sys
from pathlib import Path

import pytest

from starter.config import compose_typed_config, redact_secrets
from starter.config.core.validate import validate_config


def test_default_config_compose() -> None:
    cfg = compose_typed_config()

    assert cfg.app.name == "starter"
    assert cfg.env.name == "local"
    assert cfg.runtime.profile == "default"
    assert cfg.tracking["backend"] == "disabled"
    assert cfg.logging["backend"] == "console"
    # repo_root resolves to cwd — just verify it's an absolute path
    assert Path(cfg.paths.repo_root).is_absolute()
    assert cfg.paths.config_root.endswith("/conf")


def test_override_config_groups() -> None:
    cfg = compose_typed_config(["env=ci", "runtime=debug", "paths=test"])

    assert cfg.env.name == "ci"
    assert cfg.runtime.debug is True
    assert cfg.paths.output_dir.endswith("/tests/.outputs")


def test_wandb_requires_api_key_for_online_mode() -> None:
    cfg = compose_typed_config(["tracking=wandb", "tracking.wandb.mode=online"], validate=False)

    try:
        validate_config(cfg)
    except ValueError as exc:
        assert "WANDB_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected WandB validation to fail without an API key.")


def test_redaction_masks_wandb_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WANDB_API_KEY", "secret-value")
    cfg = compose_typed_config(["tracking=wandb"], validate=False)
    rendered = redact_secrets(cfg)

    assert "***REDACTED***" in rendered
    assert "secret-value" not in rendered


def test_cli_entrypoint_prints_composed_yaml() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    completed = subprocess.run(
        [sys.executable, "-m", "starter.cli", "runtime=debug", "tracking=disabled"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert "profile: debug" in completed.stdout
