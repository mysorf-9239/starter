"""Factory functions for constructing Profiler instances from config."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from omegaconf import DictConfig, OmegaConf

from ..backends.basic import BasicTabularProfiler
from ..backends.pandas import PandasProfiler
from .interfaces import Profiler
from .schema import ProfileSummary, ProfilingConfig
from .validate import validate_profiling_config


class NullProfiler:
    """No-op Profiler returned when profiling is disabled."""

    def profile_records(self, records: Sequence[Mapping[str, Any]]) -> ProfileSummary:
        """Return an empty :class:`ProfileSummary` without processing *records*.

        Args:
            records: Ignored input records.

        Returns:
            A :class:`ProfileSummary` with zero rows and columns.
        """
        del records
        return ProfileSummary(row_count=0, column_count=0, columns=[])


def parse_profiling_config(
    data: Mapping[str, Any] | DictConfig | ProfilingConfig,
) -> ProfilingConfig:
    """Parse and validate an external config mapping into a :class:`ProfilingConfig`.

    Args:
        data: Raw config as a :class:`Mapping`, :class:`DictConfig`, or an
            already-typed :class:`ProfilingConfig`.

    Returns:
        Validated :class:`ProfilingConfig` instance.

    Raises:
        ValueError: If the config fails validation.
    """
    if isinstance(data, ProfilingConfig):
        cfg = data
    elif isinstance(data, DictConfig):
        cfg = cast(
            ProfilingConfig,
            OmegaConf.to_object(OmegaConf.merge(OmegaConf.structured(ProfilingConfig), data)),
        )
    else:
        cfg = cast(
            ProfilingConfig,
            OmegaConf.to_object(OmegaConf.merge(OmegaConf.structured(ProfilingConfig), dict(data))),
        )
    validate_profiling_config(cfg)
    return cfg


def build_profiler(data: Mapping[str, Any] | DictConfig | ProfilingConfig) -> Profiler:
    """Construct a :class:`Profiler` from a config section.

    Args:
        data: Profiling config as a :class:`Mapping`, :class:`DictConfig`, or
            :class:`ProfilingConfig`.

    Returns:
        A :class:`Profiler` instance for the configured backend, or a
        :class:`NullProfiler` when the backend is ``"disabled"`` or
        ``enabled`` is ``False``.

    Raises:
        ValueError: If the backend identifier is not supported.
    """
    cfg = parse_profiling_config(data)
    if cfg.backend == "disabled" or not cfg.enabled:
        return NullProfiler()
    if cfg.backend == "basic":
        return BasicTabularProfiler(cfg)
    if cfg.backend == "pandas":
        return PandasProfiler(cfg)
    raise ValueError(f"Unsupported profiling backend: {cfg.backend}")
