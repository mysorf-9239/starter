"""Factory functions for constructing ArtifactManager instances from config."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast

from omegaconf import DictConfig, OmegaConf

from .interfaces import ArtifactManager
from .schema import ArtifactsConfig
from .validate import validate_artifacts_config

if TYPE_CHECKING:
    from starter.config.core.schema import PathsSection
    from starter.tracking.core.interfaces import Tracker


def parse_artifacts_config(
    data: Mapping[str, Any] | DictConfig | ArtifactsConfig,
) -> ArtifactsConfig:
    """Parse and validate an external config mapping into an :class:`ArtifactsConfig`.

    Args:
        data: Raw config as a :class:`Mapping`, :class:`DictConfig`, or an
            already-typed :class:`ArtifactsConfig`.

    Returns:
        Validated :class:`ArtifactsConfig` instance.

    Raises:
        ValueError: If the config fails validation.
    """
    if isinstance(data, ArtifactsConfig):
        cfg = data
    elif isinstance(data, DictConfig):
        cfg = cast(
            ArtifactsConfig,
            OmegaConf.to_object(OmegaConf.merge(OmegaConf.structured(ArtifactsConfig), data)),
        )
    else:
        cfg = cast(
            ArtifactsConfig,
            OmegaConf.to_object(OmegaConf.merge(OmegaConf.structured(ArtifactsConfig), dict(data))),
        )
    validate_artifacts_config(cfg)
    return cfg


def build_artifact_manager(
    data: Mapping[str, Any] | DictConfig | ArtifactsConfig,
    paths: PathsSection,
    tracker: Tracker | None = None,
    run_id: str | None = None,
) -> ArtifactManager:
    """Construct an :class:`ArtifactManager` from a config section.

    Args:
        data: Artifacts config as a :class:`Mapping`, :class:`DictConfig`, or
            :class:`ArtifactsConfig`.
        paths: :class:`PathsSection` from :class:`AppConfig`, used as the
            default ``base_dir`` when ``cfg.base_dir`` is ``None``.
        tracker: Optional tracker that receives ``log_artifact`` calls after
            each successful save.
        run_id: Run identifier used when ``versioning_strategy`` is
            ``"run_id"``.

    Returns:
        An :class:`ArtifactManager` instance, or a :class:`NullArtifactManager`
        when ``enabled`` is ``False`` or ``backend`` is ``"disabled"``.

    Raises:
        ValueError: If the backend identifier is not supported.
    """
    from ..backends.local import LocalBackend
    from ..backends.null import NullArtifactManager

    cfg = parse_artifacts_config(data)

    if not cfg.enabled or cfg.backend == "disabled":
        return NullArtifactManager()

    if cfg.backend == "local":
        base_dir = cfg.base_dir if cfg.base_dir is not None else paths.artifacts_dir
        return LocalBackend(
            base_dir=base_dir,
            versioning_strategy=cfg.versioning_strategy,
            run_id=run_id,
            tracker=tracker,
        )

    raise ValueError(
        f"Unsupported artifacts backend: {cfg.backend!r}. "
        f"Valid options: {sorted({'local', 'disabled'})}"
    )
