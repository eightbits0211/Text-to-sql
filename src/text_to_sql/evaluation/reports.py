"""Persistable evaluation summaries and deterministic breakdowns."""

import csv
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from ..data.contracts import ExampleRecord
from .metrics import EvaluationReport


@dataclass(frozen=True)
class Breakdown:
    category: str
    evaluated_count: int
    exact_match_count: int
    execution_match_count: int
    invalid_sql_count: int

    @property
    def exact_match_accuracy(self) -> float:
        return self.exact_match_count / self.evaluated_count if self.evaluated_count else 0.0

    @property
    def execution_accuracy(self) -> float:
        return self.execution_match_count / self.evaluated_count if self.evaluated_count else 0.0

    @property
    def invalid_sql_rate(self) -> float:
        return self.invalid_sql_count / self.evaluated_count if self.evaluated_count else 0.0


def build_breakdowns(
    report: EvaluationReport,
    examples: Iterable[ExampleRecord],
) -> dict[str, tuple[Breakdown, ...]]:
    """Build difficulty, query-structure, and failure-category summaries."""
    evaluations = {item.example_id: item for item in report.examples}
    records = tuple(examples)

    def summarize(categories: Iterable[tuple[str, bool, bool, bool]]) -> tuple[Breakdown, ...]:
        grouped: dict[str, list[tuple[bool, bool, bool]]] = {}
        for category, exact, execution, invalid in categories:
            grouped.setdefault(category, []).append((exact, execution, invalid))
        return tuple(
            Breakdown(
                category=category,
                evaluated_count=len(values),
                exact_match_count=sum(item[0] for item in values),
                execution_match_count=sum(item[1] for item in values),
                invalid_sql_count=sum(item[2] for item in values),
            )
            for category, values in sorted(grouped.items())
        )

    def values() -> Iterable[tuple[ExampleRecord, object]]:
        for example in records:
            evaluation = evaluations.get(example.example_id)
            if evaluation is not None:
                yield example, evaluation

    return {
        "difficulty": summarize(
            (example.difficulty.value, item.exact_match, item.execution_match, item.invalid_sql)
            for example, item in values()
        ),
        "query_structure": summarize(
            (
                example.query_structure.value,
                item.exact_match,
                item.execution_match,
                item.invalid_sql,
            )
            for example, item in values()
        ),
        "failure_category": summarize(
            (
                item.failure_category or "success",
                item.exact_match,
                item.execution_match,
                item.invalid_sql,
            )
            for _, item in values()
        ),
    }


def write_evaluation_reports(
    directory: Path,
    report: EvaluationReport,
    examples: Iterable[ExampleRecord],
) -> None:
    """Write JSON, CSV, and Markdown summaries to ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    breakdowns = build_breakdowns(report, examples)
    payload = {
        "evaluated_count": report.evaluated_count,
        "exact_match_accuracy": report.exact_match_accuracy,
        "execution_accuracy": report.execution_accuracy,
        "invalid_sql_rate": report.invalid_sql_rate,
        "examples": [asdict(item) for item in report.examples],
        "breakdowns": {
            name: [
                asdict(item)
                | {
                    "exact_match_accuracy": item.exact_match_accuracy,
                    "execution_accuracy": item.execution_accuracy,
                    "invalid_sql_rate": item.invalid_sql_rate,
                }
                for item in items
            ]
            for name, items in breakdowns.items()
        },
    }
    (directory / "evaluation.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    rows = []
    for name, items in breakdowns.items():
        rows.extend({"breakdown": name, **asdict(item)} for item in items)
    with (directory / "breakdowns.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "breakdown",
                "category",
                "evaluated_count",
                "exact_match_count",
                "execution_match_count",
                "invalid_sql_count",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Evaluation report",
        "",
        f"- Evaluated examples: {report.evaluated_count}",
        f"- Exact-match accuracy: {report.exact_match_accuracy:.4f}",
        f"- Execution accuracy: {report.execution_accuracy:.4f}",
        f"- Invalid-SQL rate: {report.invalid_sql_rate:.4f}",
        "",
    ]
    for name, items in breakdowns.items():
        lines.extend(
            [
                f"## {name.replace('_', ' ').title()}",
                "",
                "| Category | Count | EM | Exec | Invalid |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        lines.extend(
            f"| {item.category} | {item.evaluated_count} | "
            f"{item.exact_match_accuracy:.4f} | {item.execution_accuracy:.4f} | "
            f"{item.invalid_sql_rate:.4f} |"
            for item in items
        )
        lines.append("")
    (directory / "evaluation.md").write_text("\n".join(lines), encoding="utf-8")
