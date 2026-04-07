"""Schema and data models for the sweeps subsystem."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# Search space parameter types
# ---------------------------------------------------------------------------


@dataclass
class CategoricalParam:
    """A parameter with a fixed list of discrete values."""

    name: str
    values: list[Any]

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError(f"CategoricalParam {self.name!r}: values must not be empty.")


@dataclass
class IntegerParam:
    """A parameter ranging over integers."""

    name: str
    low: int
    high: int
    step: int = 1

    def __post_init__(self) -> None:
        if self.low >= self.high:
            raise ValueError(
                f"IntegerParam {self.name!r}: low ({self.low}) must be < high ({self.high})."
            )


@dataclass
class FloatParam:
    """A parameter ranging over floats."""

    name: str
    low: float
    high: float
    log_scale: bool = False
    n_points: int = 10

    def __post_init__(self) -> None:
        if self.low >= self.high:
            raise ValueError(
                f"FloatParam {self.name!r}: low ({self.low}) must be < high ({self.high})."
            )


Param = CategoricalParam | IntegerParam | FloatParam


# ---------------------------------------------------------------------------
# SearchSpace
# ---------------------------------------------------------------------------


@dataclass
class SearchSpace:
    """Collection of parameters defining the hyperparameter search space."""

    params: Sequence[Param]

    def __post_init__(self) -> None:
        if not self.params:
            raise ValueError("SearchSpace.params must not be empty.")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        result: list[dict[str, Any]] = []
        for p in self.params:
            if isinstance(p, CategoricalParam):
                result.append({"type": "categorical", "name": p.name, "values": p.values})
            elif isinstance(p, IntegerParam):
                result.append(
                    {
                        "type": "integer",
                        "name": p.name,
                        "low": p.low,
                        "high": p.high,
                        "step": p.step,
                    }
                )
            else:
                result.append(
                    {
                        "type": "float",
                        "name": p.name,
                        "low": p.low,
                        "high": p.high,
                        "log_scale": p.log_scale,
                        "n_points": p.n_points,
                    }
                )
        return {"params": result}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SearchSpace:
        """Deserialize from a plain dict."""
        if "params" not in data:
            raise ValueError("SearchSpace.from_dict: missing 'params' key.")
        params: list[Param] = []
        for item in data["params"]:
            t = item.get("type")
            if t == "categorical":
                params.append(CategoricalParam(name=item["name"], values=item["values"]))
            elif t == "integer":
                params.append(
                    IntegerParam(
                        name=item["name"],
                        low=item["low"],
                        high=item["high"],
                        step=item.get("step", 1),
                    )
                )
            elif t == "float":
                params.append(
                    FloatParam(
                        name=item["name"],
                        low=item["low"],
                        high=item["high"],
                        log_scale=item.get("log_scale", False),
                        n_points=item.get("n_points", 10),
                    )
                )
            else:
                raise ValueError(f"SearchSpace.from_dict: unknown param type {t!r}.")
        return cls(params=params)


# ---------------------------------------------------------------------------
# SweepsConfig
# ---------------------------------------------------------------------------


@dataclass
class SweepsConfig:
    """Configuration schema owned by the sweeps subsystem."""

    backend: str = "local"
    strategy: str = "grid"
    n_trials: int | None = None
    seed: int | None = None
    fail_fast: bool = False
    enabled: bool = True


# ---------------------------------------------------------------------------
# SweepResult and SweepSummary
# ---------------------------------------------------------------------------


@dataclass
class SweepResult:
    """Result of a single trial."""

    trial_index: int
    override_set: list[str]
    status: str  # "success" | "failed"
    metrics: dict[str, float] = field(default_factory=dict)
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SweepSummary:
    """Aggregated results from all trials in a sweep."""

    results: list[SweepResult]

    @property
    def n_success(self) -> int:
        return sum(1 for r in self.results if r.status == "success")

    @property
    def n_failed(self) -> int:
        return sum(1 for r in self.results if r.status == "failed")

    def best_trial(self, metric: str, mode: str = "min") -> SweepResult:
        """Return the trial with the best value for the given metric."""
        if mode not in ("min", "max"):
            raise ValueError(f"mode must be 'min' or 'max', got {mode!r}.")
        successful = [r for r in self.results if r.status == "success" and metric in r.metrics]
        if not successful:
            raise ValueError(f"No successful trials with metric {metric!r} found in sweep summary.")
        return (
            min(successful, key=lambda r: r.metrics[metric])
            if mode == "min"
            else max(successful, key=lambda r: r.metrics[metric])
        )

    def to_dataframe(self) -> Any:
        """Return a DataFrame if pandas is available, else list[dict]."""
        rows = [
            {
                "trial_index": r.trial_index,
                "status": r.status,
                "error": r.error,
                **{f"override_{i}": v for i, v in enumerate(r.override_set)},
                **r.metrics,
            }
            for r in self.results
        ]
        try:
            import pandas as pd

            return pd.DataFrame(rows)
        except ImportError:
            return rows

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = {
            "results": [
                {
                    "trial_index": r.trial_index,
                    "override_set": r.override_set,
                    "status": r.status,
                    "metrics": r.metrics,
                    "error": r.error,
                    "created_at": r.created_at.isoformat(),
                }
                for r in self.results
            ]
        }
        return json.dumps(data)

    @classmethod
    def from_json(cls, data: str) -> SweepSummary:
        """Deserialize from JSON string."""
        try:
            obj = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ValueError(f"SweepSummary.from_json: invalid JSON — {exc}") from exc
        if "results" not in obj:
            raise ValueError("SweepSummary.from_json: missing 'results' key.")
        results = []
        for item in obj["results"]:
            try:
                results.append(
                    SweepResult(
                        trial_index=item["trial_index"],
                        override_set=item["override_set"],
                        status=item["status"],
                        metrics=item.get("metrics", {}),
                        error=item.get("error"),
                        created_at=datetime.fromisoformat(item["created_at"]),
                    )
                )
            except KeyError as exc:
                raise ValueError(f"SweepSummary.from_json: missing required field {exc}.") from exc
        return cls(results=results)
