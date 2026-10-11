"""Uncertainty and paired tests on the *official* Spider metrics.

Reads ``official/official_per_example.jsonl`` written by
``run_official_spider_eval.py`` for each system and reports, per split:

* official EX, official EM and "EM-confirmed EX" (EX and EM both correct;
  a lower bound that excludes coincidental execution matches), each with a
  95% CI from a bootstrap that resamples whole databases;
* for each pair of systems: exact McNemar test, a paired database-clustered
  bootstrap CI and p-value for the difference, and Holm-adjusted p-values
  across all reported comparisons.

Usage:
    uv run python -m scripts.official_stats --split dev \
        --system lstm=<dir>/mask_render --system template=<dir>/template \
        --output <file>.json
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

from text_to_sql.evaluation.statistics import (
    cluster_bootstrap_interval,
    holm_adjust,
    mcnemar_exact,
    paired_cluster_bootstrap_difference,
)

METRICS = ("exec", "exact", "confirmed")


def load(directory: Path) -> list[dict]:
    rows = [
        json.loads(line)
        for line in (directory / "official" / "official_per_example.jsonl").read_text().splitlines()
    ]
    for row in rows:
        row["confirmed"] = int(row["exec"] and row["exact"])
    return rows


def interval_dict(interval) -> dict[str, float]:
    return {"estimate": interval.estimate, "ci95_low": interval.lower, "ci95_high": interval.upper}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", required=True)
    parser.add_argument("--system", action="append", required=True, help="name=directory")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    systems = {spec.split("=", 1)[0]: load(Path(spec.split("=", 1)[1])) for spec in args.system}
    clusters = [row["db_id"] for row in next(iter(systems.values()))]
    for rows in systems.values():
        assert [row["db_id"] for row in rows] == clusters, "systems must be aligned"

    result: dict[str, object] = {
        "split": args.split,
        "n": len(clusters),
        "systems": {},
        "pairs": {},
    }
    for name, rows in systems.items():
        result["systems"][name] = {  # type: ignore[index]
            metric: interval_dict(cluster_bootstrap_interval([r[metric] for r in rows], clusters))
            for metric in METRICS
        }
    tests = []
    for (name_a, rows_a), (name_b, rows_b) in itertools.combinations(systems.items(), 2):
        for metric in ("exec", "exact"):
            a = [r[metric] for r in rows_a]
            b = [r[metric] for r in rows_b]
            mcnemar = mcnemar_exact(a, b)
            diff, p_boot = paired_cluster_bootstrap_difference(a, b, clusters)
            tests.append(
                {
                    "pair": f"{name_a}_vs_{name_b}",
                    "metric": metric,
                    f"only_{name_a}": mcnemar.only_a,
                    f"only_{name_b}": mcnemar.only_b,
                    "mcnemar_p": mcnemar.p_value,
                    "difference": interval_dict(diff),
                    "cluster_bootstrap_p": p_boot,
                }
            )
    for key in ("mcnemar_p", "cluster_bootstrap_p"):
        for test, adjusted in zip(tests, holm_adjust([t[key] for t in tests]), strict=True):
            test[f"{key}_holm"] = adjusted
    result["pairs"] = tests
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    for name, metrics in result["systems"].items():  # type: ignore[union-attr]
        print(
            name,
            "  ".join(
                f"{m}={100 * v['estimate']:.1f} [{100 * v['ci95_low']:.1f},{100 * v['ci95_high']:.1f}]"
                for m, v in metrics.items()
            ),
        )
    for t in tests:
        print(
            f"{t['pair']:<28} {t['metric']:<6} diff={100 * t['difference']['estimate']:+.1f} "
            f"[{100 * t['difference']['ci95_low']:+.1f},{100 * t['difference']['ci95_high']:+.1f}] "
            f"mcnemar_p={t['mcnemar_p']:.3g} (holm {t['mcnemar_p_holm']:.3g}) "
            f"boot_p={t['cluster_bootstrap_p']:.3g} (holm {t['cluster_bootstrap_p_holm']:.3g})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
