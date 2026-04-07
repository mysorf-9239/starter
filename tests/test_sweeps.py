"""Tests for the sweeps subsystem."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from starter.sweeps import (
    CategoricalParam,
    FloatParam,
    IntegerParam,
    SearchSpace,
    SweepResult,
    SweepsConfig,
    SweepSummary,
    build_sweep_runner,
    run_sweep,
)
from starter.sweeps.backends.local import LocalRunner
from starter.sweeps.core.strategies import GridStrategy, RandomStrategy
from starter.sweeps.core.validate import validate_sweeps_config

# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_NAME = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"),
    min_size=1,
    max_size=20,
)


@st.composite
def valid_categorical_param(draw: Any) -> CategoricalParam:
    name = draw(_NAME)
    values = draw(st.lists(st.integers(min_value=0, max_value=100), min_size=1, max_size=5))
    return CategoricalParam(name=name, values=values)


@st.composite
def valid_integer_param(draw: Any) -> IntegerParam:
    name = draw(_NAME)
    low = draw(st.integers(min_value=0, max_value=10))
    high = draw(st.integers(min_value=low + 1, max_value=low + 10))
    return IntegerParam(name=name, low=low, high=high)


@st.composite
def valid_float_param(draw: Any) -> FloatParam:
    name = draw(_NAME)
    low = draw(st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False))
    high = draw(
        st.floats(min_value=low + 0.01, max_value=low + 1.0, allow_nan=False, allow_infinity=False)
    )
    return FloatParam(name=name, low=low, high=high, n_points=3)


@st.composite
def valid_search_space(draw: Any) -> SearchSpace:
    params = draw(
        st.lists(
            st.one_of(valid_categorical_param(), valid_integer_param(), valid_float_param()),
            min_size=1,
            max_size=3,
        )
    )
    # Ensure unique names
    seen: set[str] = set()
    unique_params = []
    for p in params:
        if p.name not in seen:
            seen.add(p.name)
            unique_params.append(p)
    if not unique_params:
        unique_params = [CategoricalParam(name="lr", values=[0.001])]
    return SearchSpace(params=unique_params)


# ---------------------------------------------------------------------------
# Public API shape
# ---------------------------------------------------------------------------


def test_public_api_exports() -> None:
    from starter.sweeps import (
        CategoricalParam,
        FloatParam,
        IntegerParam,
        SearchSpace,
        SweepResult,
        SweepRunner,
        SweepsConfig,
        SweepSummary,
        run_sweep,
    )

    assert callable(build_sweep_runner)
    assert callable(run_sweep)
    assert SearchSpace is not None
    assert SweepRunner is not None
    assert SweepSummary is not None
    assert SweepsConfig is not None
    assert SweepResult is not None
    assert CategoricalParam is not None
    assert IntegerParam is not None
    assert FloatParam is not None


# ---------------------------------------------------------------------------
# SearchSpace validation
# ---------------------------------------------------------------------------


def test_search_space_empty_params_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        SearchSpace(params=[])


def test_integer_param_low_ge_high_raises() -> None:
    with pytest.raises(ValueError, match="low"):
        IntegerParam(name="x", low=5, high=5)


def test_float_param_low_ge_high_raises() -> None:
    with pytest.raises(ValueError, match="low"):
        FloatParam(name="x", low=1.0, high=0.5)


# Feature: sweeps-subsystem, Property 1: Validation từ chối integer param với low >= high
@given(st.integers(min_value=-100, max_value=100))
@settings(max_examples=100)
def test_property_integer_param_low_ge_high(low: int) -> None:
    with pytest.raises(ValueError):
        IntegerParam(name="x", low=low, high=low)


# Feature: sweeps-subsystem, Property 2: Validation từ chối float param với low >= high
@given(st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=100)
def test_property_float_param_low_ge_high(low: float) -> None:
    with pytest.raises(ValueError):
        FloatParam(name="x", low=low, high=low)


# ---------------------------------------------------------------------------
# SweepsConfig validation
# ---------------------------------------------------------------------------


def test_validate_valid_config() -> None:
    cfg = SweepsConfig(backend="local", strategy="grid")
    validate_sweeps_config(cfg)  # must not raise


def test_validate_invalid_backend_raises() -> None:
    cfg = SweepsConfig(backend="s3")
    with pytest.raises(ValueError, match="backend"):
        validate_sweeps_config(cfg)


def test_validate_random_without_n_trials_raises() -> None:
    cfg = SweepsConfig(strategy="random", n_trials=None)
    with pytest.raises(ValueError, match="n_trials"):
        validate_sweeps_config(cfg)


# Feature: sweeps-subsystem, Property 13: Validation từ chối backend không hợp lệ
@given(st.text(min_size=1).filter(lambda s: s not in {"local", "wandb"}))
@settings(max_examples=100)
def test_property_validation_rejects_invalid_backend(backend: str) -> None:
    cfg = SweepsConfig(backend=backend)
    with pytest.raises(ValueError):
        validate_sweeps_config(cfg)


# Feature: sweeps-subsystem, Property 14: Validation từ chối random strategy thiếu n_trials
@given(st.just(None))
@settings(max_examples=100)
def test_property_validation_random_requires_n_trials(_: None) -> None:
    cfg = SweepsConfig(strategy="random", n_trials=None)
    with pytest.raises(ValueError):
        validate_sweeps_config(cfg)


# ---------------------------------------------------------------------------
# GridStrategy
# ---------------------------------------------------------------------------


def test_grid_strategy_categorical() -> None:
    space = SearchSpace(params=[CategoricalParam(name="lr", values=[0.001, 0.01, 0.1])])
    sets = GridStrategy().generate(space)
    assert len(sets) == 3
    assert all(len(s) == 1 for s in sets)


def test_grid_strategy_two_params() -> None:
    space = SearchSpace(
        params=[
            CategoricalParam(name="lr", values=[0.001, 0.01]),
            CategoricalParam(name="bs", values=[16, 32]),
        ]
    )
    sets = GridStrategy().generate(space)
    assert len(sets) == 4


def test_grid_strategy_override_format() -> None:
    space = SearchSpace(params=[CategoricalParam(name="lr", values=[0.001])])
    sets = GridStrategy().generate(space)
    assert sets[0][0] == "lr=0.001"


# Feature: sweeps-subsystem, Property 3: Grid strategy sinh đúng số lượng override sets
@given(valid_search_space())
@settings(max_examples=50)
def test_property_grid_strategy_count(space: SearchSpace) -> None:
    from starter.sweeps.core.strategies import _param_values

    expected = 1
    for p in space.params:
        expected *= len(_param_values(p))
    sets = GridStrategy().generate(space)
    assert len(sets) == expected


# Feature: sweeps-subsystem, Property 4: Grid strategy không sinh duplicate override sets
@given(st.lists(valid_categorical_param(), min_size=1, max_size=3))
@settings(max_examples=50)
def test_property_grid_strategy_no_duplicates(params: list[CategoricalParam]) -> None:
    # Ensure unique names and unique values per param
    seen: set[str] = set()
    unique = []
    for p in params:
        if p.name not in seen:
            seen.add(p.name)
            deduped_values = list(dict.fromkeys(p.values))  # preserve order, remove dups
            if deduped_values:
                unique.append(CategoricalParam(name=p.name, values=deduped_values))
    if not unique:
        unique = [CategoricalParam(name="lr", values=[0.001])]
    space = SearchSpace(params=unique)
    sets = GridStrategy().generate(space)
    as_tuples = [tuple(s) for s in sets]
    assert len(as_tuples) == len(set(as_tuples))


# Feature: sweeps-subsystem, Property 6: Override sets có format list[str] hợp lệ
@given(valid_search_space())
@settings(max_examples=50)
def test_property_override_format_grid(space: SearchSpace) -> None:
    sets = GridStrategy().generate(space)
    for override_set in sets:
        assert isinstance(override_set, list)
        for item in override_set:
            assert isinstance(item, str)
            assert "=" in item


# ---------------------------------------------------------------------------
# RandomStrategy
# ---------------------------------------------------------------------------


def test_random_strategy_count() -> None:
    space = SearchSpace(params=[CategoricalParam(name="lr", values=[0.001, 0.01, 0.1])])
    sets = RandomStrategy(n_trials=5, seed=42).generate(space)
    assert len(sets) == 5


# Feature: sweeps-subsystem, Property 5: Random strategy sinh đúng n_trials override sets
@given(st.integers(min_value=1, max_value=20))
@settings(max_examples=100)
def test_property_random_strategy_count(n: int) -> None:
    space = SearchSpace(params=[CategoricalParam(name="lr", values=[0.001, 0.01])])
    sets = RandomStrategy(n_trials=n, seed=0).generate(space)
    assert len(sets) == n


# Feature: sweeps-subsystem, Property 7: Random strategy tái lập với cùng seed
@given(st.integers(min_value=0, max_value=9999))
@settings(max_examples=100)
def test_property_random_strategy_reproducible(seed: int) -> None:
    space = SearchSpace(params=[CategoricalParam(name="lr", values=[0.001, 0.01, 0.1])])
    sets1 = RandomStrategy(n_trials=5, seed=seed).generate(space)
    sets2 = RandomStrategy(n_trials=5, seed=seed).generate(space)
    assert sets1 == sets2


# Feature: sweeps-subsystem, Property 6: Override sets format (random)
@given(valid_search_space())
@settings(max_examples=50)
def test_property_override_format_random(space: SearchSpace) -> None:
    sets = RandomStrategy(n_trials=3, seed=0).generate(space)
    for override_set in sets:
        assert isinstance(override_set, list)
        for item in override_set:
            assert isinstance(item, str)
            assert "=" in item


# ---------------------------------------------------------------------------
# SweepSummary
# ---------------------------------------------------------------------------


def _make_summary(n_success: int = 2, n_failed: int = 1) -> SweepSummary:
    results = []
    for i in range(n_success):
        results.append(
            SweepResult(
                trial_index=i,
                override_set=[f"lr={i}"],
                status="success",
                metrics={"loss": float(i + 1)},
            )
        )
    for j in range(n_failed):
        results.append(
            SweepResult(
                trial_index=n_success + j,
                override_set=[f"lr={n_success + j}"],
                status="failed",
                error="oops",
            )
        )
    return SweepSummary(results=results)


def test_summary_n_success_n_failed() -> None:
    s = _make_summary(n_success=3, n_failed=2)
    assert s.n_success == 3
    assert s.n_failed == 2


def test_summary_best_trial_min() -> None:
    s = _make_summary(n_success=3)
    best = s.best_trial("loss", mode="min")
    assert best.metrics["loss"] == 1.0


def test_summary_best_trial_max() -> None:
    s = _make_summary(n_success=3)
    best = s.best_trial("loss", mode="max")
    assert best.metrics["loss"] == 3.0


def test_summary_best_trial_invalid_mode_raises() -> None:
    s = _make_summary()
    with pytest.raises(ValueError, match="mode"):
        s.best_trial("loss", mode="median")


def test_summary_best_trial_all_failed_raises() -> None:
    s = SweepSummary(
        results=[SweepResult(trial_index=0, override_set=[], status="failed", error="x")]
    )
    with pytest.raises(ValueError):
        s.best_trial("loss")


# Feature: sweeps-subsystem, Property 11: n_success + n_failed bằng tổng số trials
@given(st.integers(min_value=0, max_value=5), st.integers(min_value=0, max_value=5))
@settings(max_examples=100)
def test_property_n_success_plus_n_failed(ns: int, nf: int) -> None:
    s = _make_summary(n_success=ns, n_failed=nf)
    assert s.n_success + s.n_failed == len(s.results)


# Feature: sweeps-subsystem, Property 12: best_trial trả về đúng result
@given(st.integers(min_value=1, max_value=5))
@settings(max_examples=100)
def test_property_best_trial_min(n: int) -> None:
    results = [
        SweepResult(trial_index=i, override_set=[], status="success", metrics={"loss": float(i)})
        for i in range(n)
    ]
    s = SweepSummary(results=results)
    best = s.best_trial("loss", mode="min")
    assert best.metrics["loss"] == 0.0


# ---------------------------------------------------------------------------
# Serialization round-trips
# ---------------------------------------------------------------------------


def test_sweep_summary_json_roundtrip() -> None:
    s = _make_summary(n_success=2, n_failed=1)
    restored = SweepSummary.from_json(s.to_json())
    assert len(restored.results) == len(s.results)
    assert restored.n_success == s.n_success
    assert restored.n_failed == s.n_failed


def test_sweep_summary_from_json_invalid_raises() -> None:
    with pytest.raises(ValueError):
        SweepSummary.from_json("not json")


def test_search_space_dict_roundtrip() -> None:
    space = SearchSpace(
        params=[
            CategoricalParam(name="lr", values=[0.001, 0.01]),
            IntegerParam(name="layers", low=1, high=5),
            FloatParam(name="dropout", low=0.1, high=0.5, n_points=3),
        ]
    )
    restored = SearchSpace.from_dict(space.to_dict())
    assert len(restored.params) == len(space.params)


# Feature: sweeps-subsystem, Property 15: Round-trip serialization của SweepSummary
@given(st.integers(min_value=1, max_value=4), st.integers(min_value=0, max_value=2))
@settings(max_examples=100)
def test_property_summary_json_roundtrip(ns: int, nf: int) -> None:
    s = _make_summary(n_success=ns, n_failed=nf)
    restored = SweepSummary.from_json(s.to_json())
    assert len(restored.results) == len(s.results)
    assert restored.n_success == s.n_success
    assert restored.n_failed == s.n_failed


# Feature: sweeps-subsystem, Property 16: Round-trip serialization của SearchSpace
@given(valid_search_space())
@settings(max_examples=100)
def test_property_search_space_dict_roundtrip(space: SearchSpace) -> None:
    restored = SearchSpace.from_dict(space.to_dict())
    assert len(restored.params) == len(space.params)
    for orig, rest in zip(space.params, restored.params, strict=True):
        assert orig.name == rest.name


# ---------------------------------------------------------------------------
# LocalRunner
# ---------------------------------------------------------------------------


def test_local_runner_success() -> None:
    space = SearchSpace(params=[CategoricalParam(name="lr", values=[0.001, 0.01])])
    override_sets = GridStrategy().generate(space)

    def trial_fn(ctx: Any, params: Mapping[str, Any]) -> dict[str, float]:
        assert "lr" in params
        return {"loss": float(params["lr"])}

    runner = LocalRunner(
        base_overrides=[
            "logging=disabled",
            "tracking=disabled",
            "profiling=disabled",
            "artifacts.enabled=false",
        ]
    )
    summary = runner.run(override_sets, trial_fn)
    assert summary.n_success == 2
    assert summary.n_failed == 0


def test_local_runner_failed_trial_continues() -> None:
    space = SearchSpace(params=[CategoricalParam(name="lr", values=[0.001, 0.01, 0.1])])
    override_sets = GridStrategy().generate(space)
    call_count = [0]

    def trial_fn(ctx: Any, params: Mapping[str, Any]) -> dict[str, float]:
        call_count[0] += 1
        if call_count[0] == 2:
            raise RuntimeError("trial failed")
        return {"loss": 0.5}

    runner = LocalRunner(
        base_overrides=[
            "logging=disabled",
            "tracking=disabled",
            "profiling=disabled",
            "artifacts.enabled=false",
        ]
    )
    summary = runner.run(override_sets, trial_fn)
    assert summary.n_success == 2
    assert summary.n_failed == 1
    assert len(summary.results) == 3


def test_local_runner_fail_fast() -> None:
    space = SearchSpace(params=[CategoricalParam(name="lr", values=[0.001, 0.01, 0.1])])
    override_sets = GridStrategy().generate(space)

    def trial_fn(ctx: Any, params: Mapping[str, Any]) -> dict[str, float]:
        raise RuntimeError("always fails")

    runner = LocalRunner(
        base_overrides=[
            "logging=disabled",
            "tracking=disabled",
            "profiling=disabled",
            "artifacts.enabled=false",
        ],
        fail_fast=True,
    )
    summary = runner.run(override_sets, trial_fn)
    assert len(summary.results) == 1
    assert summary.n_failed == 1


# Feature: sweeps-subsystem, Property 8: Local runner ghi lại đúng trạng thái
def test_property_local_runner_success_status() -> None:
    space = SearchSpace(params=[CategoricalParam(name="lr", values=[0.001])])
    override_sets = GridStrategy().generate(space)

    def trial_fn(ctx: Any, params: Mapping[str, Any]) -> dict[str, float]:
        return {"loss": 1.0}

    runner = LocalRunner(
        base_overrides=[
            "logging=disabled",
            "tracking=disabled",
            "profiling=disabled",
            "artifacts.enabled=false",
        ]
    )
    summary = runner.run(override_sets, trial_fn)
    assert all(r.status == "success" for r in summary.results)
    assert all(r.metrics for r in summary.results)


# Feature: sweeps-subsystem, Property 10: fail_fast dừng sau trial đầu tiên thất bại
def test_property_fail_fast_stops_after_first_failure() -> None:
    space = SearchSpace(params=[CategoricalParam(name="lr", values=[0.001, 0.01, 0.1])])
    override_sets = GridStrategy().generate(space)

    def trial_fn(ctx: Any, params: Mapping[str, Any]) -> dict[str, float]:
        raise RuntimeError("fail")

    runner = LocalRunner(
        base_overrides=[
            "logging=disabled",
            "tracking=disabled",
            "profiling=disabled",
            "artifacts.enabled=false",
        ],
        fail_fast=True,
    )
    summary = runner.run(override_sets, trial_fn)
    assert len(summary.results) == 1
    assert summary.results[0].status == "failed"


# ---------------------------------------------------------------------------
# run_sweep integration
# ---------------------------------------------------------------------------


def test_run_sweep_integration() -> None:
    ctx = MagicMock()
    ctx.tracker = MagicMock()
    ctx.artifact_manager = MagicMock()
    space = SearchSpace(params=[CategoricalParam(name="lr", values=[0.001, 0.01])])
    cfg = SweepsConfig(backend="local", strategy="grid")

    def trial_fn(trial_ctx: Any, params: Mapping[str, Any]) -> dict[str, float]:
        assert "lr" in params
        return {"loss": float(params["lr"])}

    summary = run_sweep(space, trial_fn, ctx, cfg)
    assert summary.n_success == 2
    assert summary.n_failed == 0
