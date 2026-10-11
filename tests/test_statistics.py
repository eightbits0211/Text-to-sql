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
