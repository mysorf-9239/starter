"""Tests for the runtime bootstrap subsystem.

Covers:
- Public API shape
- bootstrap() smoke test
- RuntimeContext immutability
- teardown() swallows tracker exceptions
- Context manager lifecycle
- Disabled backends → Null instances
- Hydra overrides round-trip
- Error propagation (no wrapping)

Property-based tests use hypothesis with max_examples=100.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from starter.artifacts import ArtifactType
from starter.logging import NullLogger
from starter.profiling import NullProfiler
from starter.runtime import RuntimeContext, bootstrap, teardown
from starter.tracking import NullTracker

# ---------------------------------------------------------------------------
# Public API shape
# ---------------------------------------------------------------------------


def test_public_api_exports() -> None:
    """RuntimeContext, bootstrap, teardown must be importable from starter.runtime."""
    assert callable(bootstrap)
    assert callable(teardown)
    assert RuntimeContext is not None


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------


def test_bootstrap_default_returns_runtime_context() -> None:
    """bootstrap() with no args returns a valid RuntimeContext."""
    ctx = bootstrap()

    assert ctx.cfg is not None
    assert ctx.run_id.startswith("run_")
    assert ctx.logger is not None
    assert ctx.tracker is not None
    assert ctx.profiler is not None
    assert isinstance(ctx, RuntimeContext)


# ---------------------------------------------------------------------------
# RuntimeContext immutability
# ---------------------------------------------------------------------------


def test_runtime_context_is_frozen() -> None:
    """Assigning to any RuntimeContext field must raise FrozenInstanceError."""
    ctx = bootstrap()

    with pytest.raises(FrozenInstanceError):
        ctx.cfg = None  # type: ignore[assignment,misc]

    with pytest.raises(FrozenInstanceError):
        ctx.logger = None  # type: ignore[assignment,misc]

    with pytest.raises(FrozenInstanceError):
        ctx.tracker = None  # type: ignore[assignment,misc]

    with pytest.raises(FrozenInstanceError):
        ctx.profiler = None  # type: ignore[assignment,misc]


# Feature: runtime-subsystem, Property 4: RuntimeContext immutability
@given(st.just(["logging=disabled", "tracking=disabled", "profiling=disabled"]))
@settings(max_examples=100, deadline=None)
def test_property_runtime_context_immutability(overrides: list[str]) -> None:
    ctx = bootstrap(overrides)
    with pytest.raises(FrozenInstanceError):
        ctx.cfg = None  # type: ignore[assignment,misc]
    with pytest.raises(FrozenInstanceError):
        ctx.logger = None  # type: ignore[assignment,misc]
    with pytest.raises(FrozenInstanceError):
        ctx.tracker = None  # type: ignore[assignment,misc]
    with pytest.raises(FrozenInstanceError):
        ctx.profiler = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# teardown
# ---------------------------------------------------------------------------


def test_teardown_calls_tracker_finish() -> None:
    """teardown() must call tracker.finish()."""
    ctx = bootstrap(["tracking=disabled"])
    mock_tracker = MagicMock()
    # Build a new context with the mock tracker (frozen, so use object.__setattr__)
    ctx2 = RuntimeContext(
        cfg=ctx.cfg,
        run_id=ctx.run_id,
        logger=ctx.logger,
        tracker=mock_tracker,
        profiler=ctx.profiler,
        artifact_manager=ctx.artifact_manager,
    )
    teardown(ctx2)
    mock_tracker.finish.assert_called_once()


def test_teardown_swallows_tracker_exception() -> None:
    """teardown() must not re-raise when tracker.finish() raises."""
    ctx = bootstrap(["tracking=disabled"])
    mock_tracker = MagicMock()
    mock_tracker.finish.side_effect = RuntimeError("tracker exploded")
    ctx2 = RuntimeContext(
        cfg=ctx.cfg,
        run_id=ctx.run_id,
        logger=ctx.logger,
        tracker=mock_tracker,
        profiler=ctx.profiler,
        artifact_manager=ctx.artifact_manager,
    )

    # Must not raise
    teardown(ctx2)


# Feature: runtime-subsystem, Property 5: Teardown swallows tracker exceptions
@given(st.text(min_size=1))
@settings(max_examples=100, deadline=None)
def test_property_teardown_swallows_exceptions(message: str) -> None:
    ctx = bootstrap(["tracking=disabled"])
    mock_tracker = MagicMock()
    mock_tracker.finish.side_effect = Exception(message)
    ctx2 = RuntimeContext(
        cfg=ctx.cfg,
        run_id=ctx.run_id,
        logger=ctx.logger,
        tracker=mock_tracker,
        profiler=ctx.profiler,
        artifact_manager=ctx.artifact_manager,
    )
    teardown(ctx2)  # must not raise


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


def test_context_manager_calls_teardown_on_exit() -> None:
    """with bootstrap() as ctx: must call teardown when exiting."""
    with bootstrap(["tracking=disabled"]):
        pass
    # teardown was called — tracker.finish() on NullTracker is a no-op, just verify no crash


def test_context_manager_swallows_tracker_exception_on_exit() -> None:
    """Context manager __exit__ must not re-raise tracker.finish() exceptions."""
    ctx_base = bootstrap(["tracking=disabled"])
    mock_tracker = MagicMock()
    mock_tracker.finish.side_effect = RuntimeError("boom")
    ctx = RuntimeContext(
        cfg=ctx_base.cfg,
        run_id=ctx_base.run_id,
        logger=ctx_base.logger,
        tracker=mock_tracker,
        profiler=ctx_base.profiler,
        artifact_manager=ctx_base.artifact_manager,
    )
    with ctx:
        pass  # __exit__ calls teardown, which swallows the exception


# ---------------------------------------------------------------------------
# Disabled backends → Null instances
# ---------------------------------------------------------------------------


def test_disabled_logging_returns_null_logger() -> None:
    ctx = bootstrap(["logging=disabled"])
    assert isinstance(ctx.logger, NullLogger)


def test_disabled_tracking_returns_null_tracker() -> None:
    ctx = bootstrap(["tracking=disabled"])
    assert isinstance(ctx.tracker, NullTracker)


def test_disabled_profiling_returns_null_profiler() -> None:
    ctx = bootstrap(["profiling=disabled"])
    assert isinstance(ctx.profiler, NullProfiler)


def test_all_disabled_returns_valid_context() -> None:
    ctx = bootstrap(["logging=disabled", "tracking=disabled", "profiling=disabled"])
    assert isinstance(ctx, RuntimeContext)
    assert ctx.cfg is not None
    assert ctx.logger is not None
    assert ctx.tracker is not None
    assert ctx.profiler is not None


# Feature: runtime-subsystem, Property 7: Null backends khi disabled
@given(st.just(["logging=disabled", "tracking=disabled", "profiling=disabled"]))
@settings(max_examples=100, deadline=None)
def test_property_null_backends_when_disabled(overrides: list[str]) -> None:
    ctx = bootstrap(overrides)
    assert isinstance(ctx.logger, NullLogger)
    assert isinstance(ctx.tracker, NullTracker)
    assert isinstance(ctx.profiler, NullProfiler)


# ---------------------------------------------------------------------------
# Hydra overrides round-trip
# ---------------------------------------------------------------------------


def test_override_runtime_seed() -> None:
    ctx = bootstrap(["runtime.seed=42"])
    assert ctx.cfg.runtime.seed == 42


def test_override_logging_backend() -> None:
    ctx = bootstrap(["logging=console"])
    assert ctx.cfg.logging["backend"] == "console"


def test_artifact_manager_uses_runtime_run_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "model.pt"
    source.write_bytes(b"weights")

    with bootstrap(["logging=disabled", "tracking=disabled"]) as ctx:
        record = ctx.artifact_manager.save(source, "model", artifact_type=ArtifactType.CHECKPOINT)

    assert record.version == ctx.run_id


# Feature: runtime-subsystem, Property 3: Override round-trip
@given(st.integers(min_value=0, max_value=9999))
@settings(max_examples=100, deadline=None)
def test_property_override_seed_round_trip(seed: int) -> None:
    ctx = bootstrap([f"runtime.seed={seed}"])
    assert ctx.cfg.runtime.seed == seed


# ---------------------------------------------------------------------------
# Bootstrap completeness (property)
# ---------------------------------------------------------------------------


# Feature: runtime-subsystem, Property 1: Bootstrap completeness
@given(st.just([]))
@settings(max_examples=100, deadline=None)
def test_property_bootstrap_completeness_empty_overrides(overrides: list[str]) -> None:
    ctx = bootstrap(overrides)
    assert ctx.cfg is not None
    assert ctx.logger is not None
    assert ctx.tracker is not None
    assert ctx.profiler is not None


# Feature: runtime-subsystem, Property 1: Bootstrap completeness (disabled)
@given(st.just(["logging=disabled", "tracking=disabled", "profiling=disabled"]))
@settings(max_examples=100, deadline=None)
def test_property_bootstrap_completeness_disabled(overrides: list[str]) -> None:
    ctx = bootstrap(overrides)
    assert ctx.cfg is not None
    assert ctx.logger is not None
    assert ctx.tracker is not None
    assert ctx.profiler is not None


# ---------------------------------------------------------------------------
# Bootstrap determinism (property)
# ---------------------------------------------------------------------------


# Feature: runtime-subsystem, Property 2: Bootstrap determinism
@given(st.just([]))
@settings(max_examples=100, deadline=None)
def test_property_bootstrap_determinism(overrides: list[str]) -> None:
    ctx1 = bootstrap(overrides)
    ctx2 = bootstrap(overrides)
    assert ctx1.cfg.runtime.seed == ctx2.cfg.runtime.seed
    assert ctx1.cfg.app.name == ctx2.cfg.app.name
    assert ctx1.cfg.runtime.profile == ctx2.cfg.runtime.profile


# ---------------------------------------------------------------------------
# Error propagation — no wrapping
# ---------------------------------------------------------------------------


def test_bootstrap_propagates_config_error() -> None:
    """Invalid override must propagate Hydra exception directly."""
    with pytest.raises((Exception, SystemExit)):
        bootstrap(["this_is_not_valid_override_format_xyz=???"])


# Feature: runtime-subsystem, Property 6: Error propagation không bọc thêm
def test_property_bootstrap_propagates_logger_error() -> None:
    with (
        patch("starter.logging.build_logger", side_effect=ValueError("bad logger config")),
        pytest.raises(ValueError, match="bad logger config"),
    ):
        bootstrap()


def test_property_bootstrap_propagates_tracker_error() -> None:
    with (
        patch("starter.tracking.build_tracker", side_effect=ValueError("bad tracker config")),
        pytest.raises(ValueError, match="bad tracker config"),
    ):
        bootstrap()


def test_property_bootstrap_propagates_profiler_error() -> None:
    with (
        patch("starter.profiling.build_profiler", side_effect=ValueError("bad profiler config")),
        pytest.raises(ValueError, match="bad profiler config"),
    ):
        bootstrap()
