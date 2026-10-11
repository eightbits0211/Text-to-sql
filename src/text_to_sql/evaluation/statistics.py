"""Uncertainty estimates and paired significance tests for per-example outcomes."""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Interval:
    estimate: float
    lower: float
    upper: float


@dataclass(frozen=True)
class McNemarResult:
    """Exact two-sided McNemar test on paired binary outcomes.

    ``only_a``: examples system A gets right and B gets wrong; ``only_b`` the reverse.
    """

    only_a: int
    only_b: int
    p_value: float


def bootstrap_interval(
    outcomes: Sequence[bool],
    *,
    resamples: int = 10_000,
    confidence: float = 0.95,
    seed: int = 42,
) -> Interval:
    """Percentile bootstrap confidence interval for a proportion."""
    count = len(outcomes)
    if count == 0:
        return Interval(0.0, 0.0, 0.0)
    values = [1 if outcome else 0 for outcome in outcomes]
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(values, k=count)) / count for _ in range(resamples))
    tail = (1.0 - confidence) / 2.0
    lower = means[math.floor(tail * (resamples - 1))]
    upper = means[math.ceil((1.0 - tail) * (resamples - 1))]
    return Interval(sum(values) / count, lower, upper)


def wilson_interval(successes: int, count: int, z: float = 1.959964) -> Interval:
    """Wilson score interval; well behaved for proportions near 0."""
    if count == 0:
        return Interval(0.0, 0.0, 0.0)
    proportion = successes / count
    denominator = 1 + z * z / count
    centre = (proportion + z * z / (2 * count)) / denominator
    margin = z * math.sqrt(proportion * (1 - proportion) / count + z * z / (4 * count * count))
    return Interval(
        proportion, max(0.0, centre - margin / denominator), min(1.0, centre + margin / denominator)
    )


def mcnemar_exact(outcomes_a: Sequence[bool], outcomes_b: Sequence[bool]) -> McNemarResult:
    """Exact (binomial) two-sided McNemar test for paired system outcomes."""
    if len(outcomes_a) != len(outcomes_b):
        raise ValueError("paired outcomes must have the same length")
    only_a = sum(1 for a, b in zip(outcomes_a, outcomes_b, strict=True) if a and not b)
    only_b = sum(1 for a, b in zip(outcomes_a, outcomes_b, strict=True) if b and not a)
    discordant = only_a + only_b
    if discordant == 0:
        return McNemarResult(only_a, only_b, 1.0)
    smaller = min(only_a, only_b)
    tail = sum(math.comb(discordant, k) for k in range(smaller + 1)) / 2**discordant
    return McNemarResult(only_a, only_b, min(1.0, 2 * tail))


def mean_and_std(values: Sequence[float]) -> tuple[float, float]:
    """Sample mean and (n-1) standard deviation."""
    if not values:
        return 0.0, 0.0
    mean = sum(values) / len(values)
    if len(values) == 1:
        return mean, 0.0
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return mean, math.sqrt(variance)


__all__ = [
    "Interval",
    "McNemarResult",
    "bootstrap_interval",
    "mcnemar_exact",
    "mean_and_std",
    "wilson_interval",
]
