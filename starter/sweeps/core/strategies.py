"""Override set generation strategies for the sweeps subsystem."""

from __future__ import annotations

import itertools
import math
import random as _random
from typing import Any

from .schema import CategoricalParam, IntegerParam, SearchSpace


def _param_values(param: Any) -> list[Any]:
    """Expand a parameter into its list of candidate values."""
    if isinstance(param, CategoricalParam):
        return list(param.values)
    if isinstance(param, IntegerParam):
        return list(range(param.low, param.high, param.step))
    # FloatParam
    if param.n_points < 2:
        return [param.low]
    if param.log_scale:
        log_low = math.log(param.low) if param.low > 0 else math.log(1e-12)
        log_high = math.log(param.high)
        step = (log_high - log_low) / (param.n_points - 1)
        return [math.exp(log_low + i * step) for i in range(param.n_points)]
    step = (param.high - param.low) / (param.n_points - 1)
    return [param.low + i * step for i in range(param.n_points)]


def _to_override(name: str, value: Any) -> str:
    return f"{name}={value}"


class GridStrategy:
    """Generate all Cartesian product combinations from a SearchSpace."""

    def generate(self, space: SearchSpace) -> list[list[str]]:
        names = [p.name for p in space.params]
        value_lists = [_param_values(p) for p in space.params]
        result = []
        for combo in itertools.product(*value_lists):
            override_set = [_to_override(n, v) for n, v in zip(names, combo, strict=True)]
            result.append(override_set)
        return result


class RandomStrategy:
    """Sample n_trials random combinations from a SearchSpace."""

    def __init__(self, n_trials: int, seed: int | None = None) -> None:
        self._n_trials = n_trials
        self._rng = _random.Random(seed)  # nosec B311

    def generate(self, space: SearchSpace) -> list[list[str]]:
        result = []
        for _ in range(self._n_trials):
            override_set = []
            for param in space.params:
                if isinstance(param, CategoricalParam):
                    value = self._rng.choice(param.values)
                elif isinstance(param, IntegerParam):
                    value = self._rng.randrange(param.low, param.high, param.step)
                else:
                    if param.log_scale and param.low > 0:
                        log_val = self._rng.uniform(math.log(param.low), math.log(param.high))
                        value = math.exp(log_val)
                    else:
                        value = self._rng.uniform(param.low, param.high)
                override_set.append(_to_override(param.name, value))
            result.append(override_set)
        return result
