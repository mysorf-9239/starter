"""Pandas-backed profiling adapter."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from importlib import import_module
from typing import Any

from ..core.schema import ColumnProfile, NumericSummary, ProfileSummary, ProfilingConfig


class PandasProfiler:
    """Profile pandas DataFrames and convert results into the core summary model."""

    def __init__(self, cfg: ProfilingConfig) -> None:
        self._cfg = cfg

    def profile_records(self, records: Sequence[Mapping[str, Any]]) -> ProfileSummary:
        """Profile record-oriented data by materializing a pandas DataFrame."""
        pd = self._import_pandas()
        frame = pd.DataFrame(list(records))
        return self.profile_dataframe(frame)

    def profile_dataframe(self, frame: object) -> ProfileSummary:
        pd = self._import_pandas()

        if not isinstance(frame, pd.DataFrame):
            raise TypeError("profile_dataframe expects a pandas.DataFrame instance.")

        working = frame
        if self._cfg.sample_size is not None and len(frame) > self._cfg.sample_size:
            working = frame.head(self._cfg.sample_size)

        columns: list[ColumnProfile] = []
        for name in working.columns:
            series = working[name]
            non_null = series.dropna()
            rendered = [str(value) for value in non_null.tolist()]
            sample_values = [value for value, _ in Counter(rendered).most_common(self._cfg.top_k)]
            numeric_summary = None

            if self._cfg.numeric_stats and pd.api.types.is_numeric_dtype(series):
                numeric_values = non_null.astype(float)
                if not numeric_values.empty:
                    numeric_summary = NumericSummary(
                        count=int(numeric_values.shape[0]),
                        minimum=float(numeric_values.min()),
                        maximum=float(numeric_values.max()),
                        mean=float(numeric_values.mean()),
                    )

            columns.append(
                ColumnProfile(
                    name=str(name),
                    non_null_count=int(non_null.shape[0]),
                    null_count=int(series.isna().sum()),
                    unique_count=int(non_null.nunique()),
                    sample_values=sample_values,
                    numeric=numeric_summary,
                )
            )

        return ProfileSummary(
            row_count=int(working.shape[0]),
            column_count=int(working.shape[1]),
            columns=columns,
        )

    @staticmethod
    def _import_pandas() -> Any:
        try:
            return import_module("pandas")
        except ImportError as exc:
            raise RuntimeError(
                "pandas is not installed. Install starter with the 'profiling-pandas' extra."
            ) from exc
