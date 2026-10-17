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


def cluster_bootstrap_interval(
    outcomes: Sequence[bool],
    clusters: Sequence[str],
    *,
    resamples: int = 10_000,
    confidence: float = 0.95,
    seed: int = 42,
) -> Interval:
    """Bootstrap CI for a proportion, resampling whole clusters (e.g. databases).

    Questions on the same database (and Spider's paraphrase pairs) are not
    independent, so an example-level bootstrap understates the uncertainty.
    """
    groups: dict[str, list[int]] = {}
    for outcome, cluster in zip(outcomes, clusters, strict=True):
        groups.setdefault(cluster, []).append(1 if outcome else 0)
    keys = sorted(groups)
    if not keys:
        return Interval(0.0, 0.0, 0.0)
    sums = [sum(groups[k]) for k in keys]
    sizes = [len(groups[k]) for k in keys]
    rng = random.Random(seed)
    estimates = []
    for _ in range(resamples):
        picks = [rng.randrange(len(keys)) for _ in keys]
        estimates.append(sum(sums[i] for i in picks) / sum(sizes[i] for i in picks))
    estimates.sort()
    tail = (1.0 - confidence) / 2.0
    return Interval(
        sum(sums) / sum(sizes),
        estimates[math.floor(tail * (resamples - 1))],
        estimates[math.ceil((1.0 - tail) * (resamples - 1))],
    )


def paired_cluster_bootstrap_difference(
    outcomes_a: Sequence[bool],
    outcomes_b: Sequence[bool],
    clusters: Sequence[str],
    *,
    resamples: int = 10_000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[Interval, float]:
    """CI for accuracy(A) - accuracy(B) and a two-sided bootstrap p-value.

    Whole clusters are resampled and both systems are scored on the same
    resample, preserving the pairing.
    """
    groups: dict[str, list[tuple[int, int]]] = {}
    for a, b, cluster in zip(outcomes_a, outcomes_b, clusters, strict=True):
        groups.setdefault(cluster, []).append((1 if a else 0, 1 if b else 0))
    keys = sorted(groups)
    diff_sums = [sum(a - b for a, b in groups[k]) for k in keys]
    sizes = [len(groups[k]) for k in keys]
    observed = sum(diff_sums) / sum(sizes)
    rng = random.Random(seed)
    diffs = []
    for _ in range(resamples):
        picks = [rng.randrange(len(keys)) for _ in keys]
        diffs.append(sum(diff_sums[i] for i in picks) / sum(sizes[i] for i in picks))
    diffs.sort()
    tail = (1.0 - confidence) / 2.0
    below = sum(1 for d in diffs if d <= 0) / resamples
    above = sum(1 for d in diffs if d >= 0) / resamples
    p_value = min(1.0, 2 * min(below, above))
    interval = Interval(
        observed,
        diffs[math.floor(tail * (resamples - 1))],
        diffs[math.ceil((1.0 - tail) * (resamples - 1))],
    )
    return interval, p_value


def holm_adjust(p_values: Sequence[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values (family-wise error control)."""
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    adjusted = [0.0] * len(p_values)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (len(p_values) - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


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
    "cluster_bootstrap_interval",
    "holm_adjust",
    "mcnemar_exact",
    "mean_and_std",
    "paired_cluster_bootstrap_difference",
    "wilson_interval",
]
