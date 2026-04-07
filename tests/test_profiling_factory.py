from starter.config import compose_typed_config
from starter.profiling import NullProfiler, build_profiler, parse_profiling_config


def test_config_compose_includes_profiling_section() -> None:
    cfg = compose_typed_config()

    assert cfg.profiling["backend"] == "basic"
    assert cfg.profiling["enabled"] is True


def test_build_disabled_profiler_returns_null_profiler() -> None:
    cfg = compose_typed_config(["profiling=disabled"])
    profiler = build_profiler(cfg.profiling)

    assert isinstance(profiler, NullProfiler)


def test_basic_profiler_summarizes_python_records() -> None:
    cfg = compose_typed_config(["profiling=basic"])
    profiler = build_profiler(cfg.profiling)
    summary = profiler.profile_records(
        [
            {"drug": "A", "score": 1.0, "label": 1},
            {"drug": "B", "score": 2.0, "label": 0},
            {"drug": "A", "score": None, "label": 1},
        ]
    )

    assert summary.row_count == 3
    assert summary.column_count == 3
    by_name = {column.name: column for column in summary.columns}
    assert by_name["drug"].unique_count == 2
    assert by_name["score"].null_count == 1
    assert by_name["label"].numeric is not None
    assert by_name["label"].numeric.mean == 2 / 3


def test_parse_pandas_profiling_config() -> None:
    cfg = parse_profiling_config(
        {
            "backend": "pandas",
            "enabled": True,
            "top_k": 3,
            "numeric_stats": True,
            "sample_size": 100,
        }
    )

    assert cfg.backend == "pandas"
    assert cfg.sample_size == 100
