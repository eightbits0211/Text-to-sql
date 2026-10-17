"""Diagnostics for Part 2 predictions: CIs, error taxonomy, schema linking, audits.

Reads ``predictions.jsonl`` artifacts (any model) plus the dataset records,
re-scores them with the current harness, and writes ``analysis.json`` and
``analysis.md``. Nothing here changes predictions.

Usage:
    uv run python -m scripts.analyze_part2 --dataset spider --split dev \
        --model lstm=.../mask_render/predictions.jsonl \
        --model template=.../template/predictions.jsonl \
        --output-dir .../analysis/spider-dev
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from scripts.run_ablation import load_records
from text_to_sql.data.contracts import ExampleRecord
from text_to_sql.evaluation.metrics import (
    ExampleEvaluation,
    Prediction,
    evaluate_predictions,
    execute_read_only,
)
from text_to_sql.evaluation.statistics import mcnemar_exact, wilson_interval
from text_to_sql.lstm.rendering import SCHEMA_MARKUP_TOKENS, schema_name_map

_LITERAL = re.compile(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"")
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_AGGREGATES = ("count", "sum", "avg", "min", "max")


def _strip_literals(sql: str, names: dict[str, str]) -> str:
    """Replace value literals with <v>; double-quoted schema identifiers are kept."""

    def replace(match: re.Match[str]) -> str:
        text = match.group(0)
        if text.startswith('"') and text[1:-1].lower() in names:
            return text[1:-1]
        return " <v> "

    return _LITERAL.sub(replace, sql)


def _literals(sql: str) -> list[str]:
    return [m.group(0)[1:-1] for m in re.finditer(r"'(?:[^']|'')*'", sql)]


def sql_features(sql: str, names: dict[str, str]) -> dict[str, object]:
    """Coarse structural signature of a SQL string (literals ignored)."""
    body = _strip_literals(sql, names).lower()
    words = _WORD.findall(body)
    identifiers = {w for w in words if w in names}
    from_tables = set(re.findall(r"\b(?:from|join)\s+\"?([a-z_][a-z0-9_]*)", body))
    return {
        "tables": {t for t in from_tables if t in names},
        "identifiers": identifiers,
        "aggregates": Counter(a for a in _AGGREGATES if re.search(rf"\b{a}\s*\(", body)),
        "select_items": len(body.split(" from ", 1)[0].split(",")) if " from " in body else 0,
        "joins": len(re.findall(r"\bjoin\b", body)),
        "where": bool(re.search(r"\bwhere\b", body)),
        "group": bool(re.search(r"\bgroup\s+by\b", body)),
        "having": bool(re.search(r"\bhaving\b", body)),
        "order": bool(re.search(r"\border\s+by\b", body)),
        "limit": bool(re.search(r"\blimit\b", body)),
        "nested": body.count("select") > 1,
        "set_op": bool(re.search(r"\b(union|intersect|except)\b", body)),
        "distinct": bool(re.search(r"\bdistinct\b", body)),
        "words": set(words),
    }


def error_flags(
    gold: dict[str, object], pred: dict[str, object], gold_sql: str, pred_sql: str, names: dict
) -> list[str]:
    flags = []
    leaked = (pred["words"] & SCHEMA_MARKUP_TOKENS) - set(names)  # type: ignore[operator]
    if leaked:
        flags.append("schema_markup_token_leak")
    if pred["tables"] != gold["tables"]:
        flags.append("wrong_table_set")
    if pred["joins"] != gold["joins"]:
        flags.append("join_count_mismatch")
    if pred["aggregates"] != gold["aggregates"]:
        flags.append("aggregation_mismatch")
    if pred["select_items"] != gold["select_items"]:
        flags.append("projection_count_mismatch")
    if (pred["identifiers"] - gold["identifiers"]) or (gold["identifiers"] - pred["identifiers"]):  # type: ignore[operator]
        flags.append("column_mismatch")
    for clause in ("where", "group", "having", "order", "limit", "nested", "set_op"):
        if pred[clause] != gold[clause]:
            flags.append(f"{clause}_mismatch")
    gold_values, pred_values = _literals(gold_sql), _literals(pred_sql)
    if sorted(v.lower() for v in gold_values) != sorted(v.lower() for v in pred_values):
        flags.append("value_mismatch")
    elif sorted(gold_values) != sorted(pred_values):
        flags.append("value_case_only_mismatch")
    return flags


ROOT_CAUSE_ORDER = (
    "invalid_sql",
    "wrong_table_set",
    "wrong_columns",
    "wrong_clause_structure",
    "wrong_aggregation",
    "wrong_projection_count",
    "wrong_values",
    "other_same_signature",
)


def root_cause(flags: list[str], invalid: bool) -> str:
    """First failing component, checked in a fixed priority order (one label per failure)."""
    if invalid:
        return "invalid_sql"
    present = set(flags)
    if "wrong_table_set" in present:
        return "wrong_table_set"
    if "column_mismatch" in present:
        return "wrong_columns"
    structure = {
        "join_count_mismatch",
        "where_mismatch",
        "group_mismatch",
        "having_mismatch",
        "order_mismatch",
        "limit_mismatch",
        "nested_mismatch",
        "set_op_mismatch",
    }
    if present & structure:
        return "wrong_clause_structure"
    if "aggregation_mismatch" in present:
        return "wrong_aggregation"
    if "projection_count_mismatch" in present:
        return "wrong_projection_count"
    if present & {"value_mismatch", "value_case_only_mismatch"}:
        return "wrong_values"
    return "other_same_signature"


def schema_linking(gold: dict, pred: dict) -> tuple[int, int, int]:
    """(true positives, predicted, gold) over referenced schema identifiers."""
    g, p = gold["identifiers"], pred["identifiers"]
    return len(g & p), len(p), len(g)


def analyze_model(
    records: tuple[ExampleRecord, ...], rows: list[dict]
) -> tuple[dict[str, object], tuple[ExampleEvaluation, ...]]:
    by_id = {row["example_id"]: row for row in rows}
    predictions = tuple(
        Prediction(r.example_id, "m", by_id.get(r.example_id, {}).get("predicted_sql", ""))
        for r in records
    )
    report = evaluate_predictions(records, predictions)
    flags_counter: Counter[str] = Counter()
    root_causes: Counter[str] = Counter()
    root_by_difficulty: dict[str, Counter[str]] = {}
    error_classes: Counter[str] = Counter()
    link_tp = link_pred = link_gold = 0
    table_tp = table_pred = table_gold = 0
    ex_hits_without_sm: Counter[str] = Counter()
    per_structure: dict[str, list[bool]] = {}
    per_difficulty: dict[str, list[bool]] = {}
    for record, prediction, item in zip(records, predictions, report.examples, strict=True):
        names = {k.lower(): v for k, v in schema_name_map(record.schema_text).items()}
        gold = sql_features(record.gold_sql, names)
        pred = sql_features(prediction.predicted_sql, names)
        tp, np_, ng = schema_linking(gold, pred)
        link_tp, link_pred, link_gold = link_tp + tp, link_pred + np_, link_gold + ng
        table_tp += len(gold["tables"] & pred["tables"])  # type: ignore[operator]
        table_pred += len(pred["tables"])  # type: ignore[arg-type]
        table_gold += len(gold["tables"])  # type: ignore[arg-type]
        per_structure.setdefault(record.query_structure.value, []).append(item.execution_match)
        per_difficulty.setdefault(record.difficulty.value, []).append(item.execution_match)
        if item.invalid_sql:
            error_classes[item.error_class or "other"] += 1
        if not item.execution_match:
            flags = error_flags(gold, pred, record.gold_sql, prediction.predicted_sql, names)
            for flag in flags:
                flags_counter[flag] += 1
            cause = root_cause(flags, item.invalid_sql)
            root_causes[cause] += 1
            root_by_difficulty.setdefault(record.difficulty.value, Counter())[cause] += 1
        elif not item.exact_match:
            structural = [
                f
                for f in error_flags(gold, pred, record.gold_sql, prediction.predicted_sql, names)
                if f not in ("value_case_only_mismatch", "projection_count_mismatch")
            ]
            result = execute_read_only(
                record.gold_sql, record.database_path, record.execution_prelude
            )
            if not structural:
                ex_hits_without_sm["equivalent_structure"] += 1
            elif not result.rows or result.rows in (((0,),), ((None,),)):
                ex_hits_without_sm["coincidental_empty_or_zero_result"] += 1
            else:
                ex_hits_without_sm["coincidental_structure_differs"] += 1

    def interval(values: list[bool]) -> dict[str, float]:
        ci = wilson_interval(sum(values), len(values))
        return {
            "n": len(values),
            "estimate": ci.estimate,
            "ci95_low": ci.lower,
            "ci95_high": ci.upper,
        }

    failures = sum(1 for item in report.examples if not item.execution_match)
    summary = {
        "n": report.evaluated_count,
        "execution_strict": interval([i.execution_match for i in report.examples]),
        "execution_official_semantics": interval(
            [i.execution_match_official for i in report.examples]
        ),
        "string_match": interval([i.exact_match for i in report.examples]),
        "invalid_sql": interval([i.invalid_sql for i in report.examples]),
        "empty_predictions": sum(1 for p in predictions if not p.predicted_sql.strip()),
        "invalid_sql_error_classes": dict(error_classes.most_common()),
        "failure_flags": {"failures": failures, **dict(flags_counter.most_common())},
        "root_cause": {k: root_causes.get(k, 0) for k in ROOT_CAUSE_ORDER},
        "root_cause_by_difficulty": {
            level: {k: counts.get(k, 0) for k in ROOT_CAUSE_ORDER}
            for level, counts in sorted(root_by_difficulty.items())
        },
        "execution_hits_without_string_match": dict(ex_hits_without_sm),
        "schema_linking": {
            "identifier_precision": link_tp / link_pred if link_pred else 0.0,
            "identifier_recall": link_tp / link_gold if link_gold else 0.0,
            "table_precision": table_tp / table_pred if table_pred else 0.0,
            "table_recall": table_tp / table_gold if table_gold else 0.0,
        },
        "execution_by_structure": {k: interval(v) for k, v in sorted(per_structure.items())},
        "execution_by_difficulty": {k: interval(v) for k, v in sorted(per_difficulty.items())},
    }
    return summary, report.examples


def gold_through_gold(records: tuple[ExampleRecord, ...]) -> dict[str, object]:
    predictions = tuple(Prediction(r.example_id, "gold", r.gold_sql) for r in records)
    report = evaluate_predictions(records, predictions)
    failures = [i.example_id for i in report.examples if not i.execution_match]
    return {
        "n": report.evaluated_count,
        "execution_strict": report.execution_accuracy,
        "execution_official_semantics": report.execution_accuracy_official,
        "string_match": report.exact_match_accuracy,
        "failures": failures[:20],
        "failure_count": len(failures),
    }


def _markdown(payload: dict[str, object]) -> str:
    lines = [f"# Part 2 analysis — {payload['dataset']} {payload['split']}", ""]
    gtg = payload["gold_through_gold"]
    lines += [
        "## Gold-through-gold sanity check",
        "",
        (
            f"- n={gtg['n']}, strict EX={gtg['execution_strict']:.4f}, "
            f"official-semantics EX={gtg['execution_official_semantics']:.4f}, "
            f"failures={gtg['failure_count']}"
        ),
        "",
    ]
    for name, summary in payload["models"].items():
        lines += [f"## {name}", "", "```json", json.dumps(summary, indent=2), "```", ""]
    if payload.get("mcnemar"):
        lines += ["## Paired McNemar tests (strict EX)", "", "```json"]
        lines += [json.dumps(payload["mcnemar"], indent=2), "```", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("spider", "wikisql"), default="spider")
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--model", action="append", default=[], help="name=predictions.jsonl")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    records = load_records(args.dataset, args.split, None)
    payload: dict[str, object] = {
        "dataset": args.dataset,
        "split": args.split,
        "gold_through_gold": gold_through_gold(records),
        "models": {},
        "mcnemar": {},
    }
    outcomes: dict[str, list[bool]] = {}
    for spec in args.model:
        name, path = spec.split("=", 1)
        rows = [json.loads(line) for line in Path(path).read_text().splitlines()]
        summary, examples = analyze_model(records, rows)
        payload["models"][name] = summary  # type: ignore[index]
        outcomes[name] = [item.execution_match for item in examples]
    names = list(outcomes)
    for i, first in enumerate(names):
        for second in names[i + 1 :]:
            test = mcnemar_exact(outcomes[first], outcomes[second])
            payload["mcnemar"][f"{first}_vs_{second}"] = {  # type: ignore[index]
                f"only_{first}": test.only_a,
                f"only_{second}": test.only_b,
                "p_value": test.p_value,
            }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "analysis.json").write_text(json.dumps(payload, indent=2))
    (args.output_dir / "analysis.md").write_text(_markdown(payload))
    print(json.dumps(payload["gold_through_gold"], indent=2))
    for name, summary in payload["models"].items():  # type: ignore[union-attr]
        print(name, json.dumps({k: summary[k] for k in ("execution_strict", "invalid_sql")}))
    print(json.dumps(payload["mcnemar"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
