import pytest

from text_to_sql.evaluation.statistics import (
    bootstrap_interval,
    mcnemar_exact,
    mean_and_std,
    wilson_interval,
)


def test_mcnemar_exact_matches_binomial_tail() -> None:
    # 1 vs 0 discordant pairs: p = 2 * P(X <= 0 | n=1) = 1.0 (a one-query "win").
    single = mcnemar_exact([True, False, False], [False, False, False])
    assert (single.only_a, single.only_b) == (1, 0)
    assert single.p_value == pytest.approx(1.0)

    # 10 vs 0 discordant pairs: p = 2 / 2**10.
    strong = mcnemar_exact([True] * 10 + [False] * 5, [False] * 15)
    assert strong.p_value == pytest.approx(2 / 1024)


def test_mcnemar_requires_paired_lengths() -> None:
    with pytest.raises(ValueError):
        mcnemar_exact([True], [True, False])


def test_bootstrap_interval_contains_estimate_and_is_deterministic() -> None:
    outcomes = [True] * 61 + [False] * 973
    first = bootstrap_interval(outcomes, resamples=2000)
    second = bootstrap_interval(outcomes, resamples=2000)

    assert first == second
    assert first.lower < first.estimate < first.upper
    assert first.estimate == pytest.approx(61 / 1034)


def test_wilson_interval_handles_zero_successes() -> None:
    interval = wilson_interval(0, 166)
    assert interval.lower == 0.0
    assert 0.0 < interval.upper < 0.03


def test_mean_and_std_uses_sample_deviation() -> None:
    mean, std = mean_and_std([1.0, 2.0, 3.0])
    assert mean == pytest.approx(2.0)
    assert std == pytest.approx(1.0)


def test_cluster_bootstrap_is_wider_than_example_bootstrap_for_clustered_data() -> None:
    from text_to_sql.evaluation.statistics import cluster_bootstrap_interval

    # 10 databases: half all-correct, half all-wrong -> strong within-cluster correlation.
    outcomes = [i < 50 for i in range(100)]
    clusters = [f"db{i // 10}" for i in range(100)]
    clustered = cluster_bootstrap_interval(outcomes, clusters, resamples=2000)
    naive = bootstrap_interval(outcomes, resamples=2000)

    assert clustered.estimate == pytest.approx(0.5)
    assert (clustered.upper - clustered.lower) > (naive.upper - naive.lower)


def test_paired_cluster_difference_detects_consistent_gain() -> None:
    from text_to_sql.evaluation.statistics import paired_cluster_bootstrap_difference

    a = [True] * 30 + [False] * 70
    b = [False] * 100
    clusters = [f"db{i % 10}" for i in range(100)]
    interval, p_value = paired_cluster_bootstrap_difference(a, b, clusters, resamples=2000)

    assert interval.estimate == pytest.approx(0.3)
    assert interval.lower > 0
    assert p_value < 0.01


def test_holm_adjust_matches_hand_computation() -> None:
    from text_to_sql.evaluation.statistics import holm_adjust

    assert holm_adjust([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
