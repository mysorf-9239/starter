"""Schema and summary models for profiling."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProfilingConfig:
    backend: str = "basic"
    enabled: bool = True
    top_k: int = 5
    numeric_stats: bool = True
    sample_size: int | None = None


@dataclass
class NumericSummary:
    count: int = 0
    minimum: float | None = None
    maximum: float | None = None
    mean: float | None = None


@dataclass
class ColumnProfile:
    name: str
    non_null_count: int
    null_count: int
    unique_count: int
    sample_values: list[str] = field(default_factory=list)
    numeric: NumericSummary | None = None


@dataclass
class ProfileSummary:
    row_count: int
    column_count: int
    columns: list[ColumnProfile] = field(default_factory=list)
