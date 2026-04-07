"""Bootstrap orchestration for the runtime subsystem."""

from __future__ import annotations

from collections.abc import Sequence

from .schema import RuntimeContext


def bootstrap(overrides: Sequence[str] | None = None) -> RuntimeContext:
    """Compose configuration and construct all subsystem instances.

    Subsystem construction order:

    1. :func:`~starter.config.compose_typed_config` — config composition and
       validation.
    2. :func:`~starter.logging.build_logger` — logging backend.
    3. :func:`~starter.tracking.build_tracker` — tracking backend.
    4. :func:`~starter.profiling.build_profiler` — profiling backend.
    5. :func:`~starter.artifacts.build_artifact_manager` — artifact manager.

    Exceptions raised by any step propagate directly without wrapping.

    Args:
        overrides: Hydra override strings applied during config composition,
            e.g. ``["logging=rich", "runtime.seed=42"]``.  Defaults to an
            empty list when ``None``.

    Returns:
        An immutable :class:`RuntimeContext` containing all subsystem
        instances.
    """
    from starter.artifacts import build_artifact_manager
    from starter.config import compose_typed_config
    from starter.logging import build_logger
    from starter.profiling import build_profiler
    from starter.tracking import build_tracker

    cfg = compose_typed_config(list(overrides) if overrides is not None else [])
    logger = build_logger(cfg.logging, name=cfg.app.name)
    tracker = build_tracker(cfg.tracking)
    profiler = build_profiler(cfg.profiling)
    artifact_manager = build_artifact_manager(cfg.artifacts, cfg.paths, tracker=tracker)

    return RuntimeContext(
        cfg=cfg,
        logger=logger,
        tracker=tracker,
        profiler=profiler,
        artifact_manager=artifact_manager,
    )


def teardown(context: RuntimeContext) -> None:
    """Release resources held by a :class:`RuntimeContext`.

    Invokes ``context.tracker.finish()``.  Any exception raised is suppressed
    after a warning is emitted via ``context.logger``, ensuring that teardown
    does not mask an exception propagating from the caller.

    Args:
        context: The runtime context to tear down.
    """
    try:
        context.tracker.finish()
    except Exception as exc:  # noqa: BLE001
        context.logger.warning(f"tracker.finish() failed during teardown: {exc}")
