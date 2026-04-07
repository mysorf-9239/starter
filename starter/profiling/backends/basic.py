"""Stdlib-only tabular profiler backend."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from statistics import fmean
from typing import Any

from ..core.schema import ColumnProfile, NumericSummary, ProfileSummary, ProfilingConfig


def _is_number(value: Any) -> bool:
    """Return ``True`` if *value* is a numeric type excluding ``bool``."""
    return isinstance(value, int | float) and not isinstance(value, bool)


class BasicTabularProfiler:
    """Profiler for record-oriented tabular data represented as Python mappings.

    Requires no external dependencies beyond the standard library.
    """

    def __init__(self, cfg: ProfilingConfig) -> None:
        self._cfg = cfg

    def profile_records(self, records: Sequence[Mapping[str, Any]]) -> ProfileSummary:
        """Compute a column-level profile over *records*.

        Args:
            records: Sequence of mappings representing tabular rows.

        Returns:
            :class:`ProfileSummary` with per-column statistics.
        """
        column_names = sorted({key for record in records for key in record})
        columns: list[ColumnProfile] = []

        for name in column_names:
            values = [record.get(name) for record in records]
            non_null = [value for value in values if value is not None]
            null_count = len(values) - len(non_null)
            rendered_non_null = [str(value) for value in non_null]
            sample_values = [
                value for value, _ in Counter(rendered_non_null).most_common(self._cfg.top_k)
            ]
            numeric_summary = None

            if self._cfg.numeric_stats:
                numeric_values = [float(value) for value in non_null if _is_number(value)]
                if numeric_values and len(numeric_values) == len(non_null):
                    numeric_summary = NumericSummary(
                        count=len(numeric_values),
                        minimum=min(numeric_values),
                        maximum=max(numeric_values),
                        mean=fmean(numeric_values),
                    )

            columns.append(
                ColumnProfile(
                    name=name,
                    non_null_count=len(non_null),
                    null_count=null_count,
                    unique_count=len(set(rendered_non_null)),
                    sample_values=sample_values,
                    numeric=numeric_summary,
                )
            )

        return ProfileSummary(
            row_count=len(records),
            column_count=len(column_names),
            columns=columns,
        )
