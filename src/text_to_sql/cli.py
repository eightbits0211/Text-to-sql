"""Command-line demo and scripted rehearsal for Part 2 Text-to-SQL baselines."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .baselines.template import TemplateBaseline
from .config import LSTM_CHECKPOINT_DIR, SPIDER_ROOT
from .data.schema import DatabaseSchema
from .data.spider import _schema_from_metadata
from .data.sqlite_schema import load_sqlite_schema
from .evaluation.metrics import ExecutionResult, _rows_match_official, execute_read_only

DEFAULT_DEMO_DB = SPIDER_ROOT / "database" / "concert_singer" / "concert_singer.sqlite"
DEFAULT_CHECKPOINT = LSTM_CHECKPOINT_DIR / "spider_checkpoint.pt"


@dataclass(frozen=True)
class DemoCase:
    name: str
    category: str
    question: str
    description: str
    gold_sql: str | None = None


SCRIPTED_DEMO_CASES: tuple[DemoCase, ...] = (
    DemoCase(
        name="Case 1 (Easy Projection)",
        category="easy",
        question="What are the names of all singers from France?",
        description="Tests single-table schema resolution, column projection, and string equality condition.",
        gold_sql="SELECT Name FROM singer WHERE Country = 'France'",
    ),
    DemoCase(
        name="Case 2 (Numeric Filter)",
        category="filter",
        question="What are the names and ages of singers older than 30?",
        description="Tests multi-column projection and numeric comparison filtering (> 30).",
        gold_sql="SELECT Name, Age FROM singer WHERE Age > 30",
    ),
    DemoCase(
        name="Case 3 (Join + Group By)",
        category="hard",
        question="Show the stadium name and the number of concerts in each stadium.",
        description="Needs a two-table join and GROUP BY: outside the template grammar, hard for the LSTM.",
        gold_sql=(
            "SELECT T2.Name, count(*) FROM concert AS T1 JOIN stadium AS T2 "
            "ON T1.Stadium_ID = T2.Stadium_ID GROUP BY T1.Stadium_ID"
        ),
    ),
)

# Verdict label -> ANSI colour code.
VERDICT_COLOURS = {
    "CORRECT": "1;32",
    "WRONG ANSWER": "1;31",
    "EXECUTION ERROR": "1;31",
    "NO SQL (refused)": "1;33",
    "RAN (not checked)": "1;36",
}


def _use_colour() -> bool:
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _style(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _use_colour() else text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate and execute SQL from natural language questions over SQLite schemas."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help="Path to SQLite database file. Defaults to concert_singer if available.",
    )
    parser.add_argument(
        "--question",
        type=str,
        default=None,
        help="Natural language question to convert to SQL.",
    )
    parser.add_argument(
        "--database-id",
        type=str,
        default="demo-database",
        help="Identifier for the database schema.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the scripted 3-case demonstration (easy, filter, failure case).",
    )
    parser.add_argument(
        "--model",
        choices=["template", "lstm", "both"],
        default="template",
        help="Baseline model to use; 'both' compares template and LSTM side by side (default: template).",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help="Path to LSTM model checkpoint if using --model lstm.",
    )
    parser.add_argument(
        "--train-demo",
        action="store_true",
        help="Train a small LSTM live on CPU (a few minutes) and evaluate it on held-out questions.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=60,
        help="Epochs for --train-demo (default: 60, about 2-3 minutes on a laptop CPU).",
    )
    parser.add_argument(
        "--train-databases",
        type=str,
        default="soccer_2",
        help="Comma-separated Spider train databases for --train-demo.",
    )
    return parser


def load_demo_schema(db_path: Path, database_id: str) -> DatabaseSchema:
    """Load the schema in the same form the models were trained on.

    For a Spider database (``.../database/<db_id>/<db_id>.sqlite``) this reads
    the official ``tables.json`` metadata, as the training loader does, so the
    LSTM sees the same serialization (``[text]``/``[number]`` types, real
    database name). Other databases fall back to SQLite introspection.
    """
    spider_root = db_path.resolve().parent.parent.parent
    for tables_name in ("tables.json", "test_tables.json"):
        tables_path = spider_root / tables_name
        if not tables_path.is_file():
            continue
        for record in json.loads(tables_path.read_text(encoding="utf-8")):
            if record.get("db_id") == db_path.stem:
                return _schema_from_metadata(record, db_path.stem)
    return load_sqlite_schema(db_path, database_id)


def format_table(columns: tuple[str, ...], rows: list[tuple[object, ...]]) -> str:
    """Render rows in a clean ASCII table."""
    if not columns:
        return "(empty columns)"
    col_widths = [len(col) for col in columns]
    for row in rows:
        for idx, val in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(str(val)))

    header = " | ".join(col.ljust(col_widths[i]) for i, col in enumerate(columns))
    divider = "-+-".join("-" * col_widths[i] for i in range(len(columns)))
    row_lines = [
        " | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row)) for row in rows
    ]
    return (
        f"{header}\n{divider}\n" + "\n".join(row_lines)
        if row_lines
        else f"{header}\n{divider}\n(0 rows)"
    )


@lru_cache(maxsize=4)
def _load_lstm(checkpoint_path: Path | None):
    """Load the LSTM once per checkpoint, so the scripted demo does not reload it per case."""
    from .lstm.adapter import LSTMBaseline

    if checkpoint_path is not None and checkpoint_path.is_file():
        return LSTMBaseline.from_checkpoint(checkpoint_path)
    return LSTMBaseline()


def predict_sql(
    question: str,
    schema: DatabaseSchema,
    model_name: str = "template",
    checkpoint_path: Path | str | None = None,
) -> str:
    if model_name == "template":
        return TemplateBaseline().predict(question, schema)
    if model_name == "lstm":
        target_ckpt = Path(checkpoint_path) if checkpoint_path else DEFAULT_CHECKPOINT
        db_id = getattr(schema, "database_id", "unknown")
        return _load_lstm(target_ckpt).predict(question, schema, database_id=db_id)
    raise ValueError(f"Unsupported model: {model_name}")


def _render_result(exec_result: ExecutionResult) -> str:
    table_str = format_table(exec_result.columns, list(exec_result.rows))
    row_count = len(exec_result.rows)
    return f"{table_str}\n({row_count} row{'s' if row_count != 1 else ''} returned)"


def judge(sql: str, db_path: Path, gold_sql: str | None) -> tuple[str, ExecutionResult | None]:
    """Execute a prediction and compare it with the gold query's result, as EX does."""
    if not sql or not sql.strip():
        return "NO SQL (refused)", None
    exec_result = execute_read_only(sql, db_path)
    if exec_result.status != "success":
        return "EXECUTION ERROR", exec_result
    if gold_sql is None:
        return "RAN (not checked)", exec_result
    gold_result = execute_read_only(gold_sql, db_path)
    if gold_result.status != "success":
        return "RAN (not checked)", exec_result
    ordered = "order by" in gold_sql.lower()
    if _rows_match_official(gold_result, exec_result, ordered):
        return "CORRECT", exec_result
    return "WRONG ANSWER", exec_result


def run_query(
    question: str,
    schema: DatabaseSchema,
    db_path: Path | str,
    model_name: str = "template",
    checkpoint_path: Path | str | None = None,
) -> tuple[str, bool, str]:
    """Generate SQL, validate, and execute. Returns (sql, is_success, output_display)."""
    db_path = Path(db_path)
    sql = predict_sql(question, schema, model_name, checkpoint_path)

    if not sql or not sql.strip():
        return (
            "",
            False,
            "UNSUPPORTED: Model emitted empty SQL (query structure is outside supported grammar).",
        )

    exec_result = execute_read_only(sql, db_path)
    if exec_result.status != "success":
        return (sql, False, f"EXECUTION ERROR: {exec_result.error}")
    return (sql, True, _render_result(exec_result))


def _print_prediction(
    model_name: str, sql: str, verdict: str, exec_result: ExecutionResult | None
) -> None:
    print(f"  {_style(model_name.upper(), '1')}")
    print(f"    SQL    : {_style(sql, '36') if sql else '(none)'}")
    print(f"    Verdict: {_style(verdict, VERDICT_COLOURS[verdict])}")
    if exec_result is None:
        print("    (no SQL: the question is outside the template grammar, so nothing is run)")
    elif exec_result.status != "success":
        print(f"    Error  : {exec_result.error}")
    else:
        for line in _render_result(exec_result).splitlines():
            print(f"      {line}")


def run_scripted_demo(
    db_path: Path | str = DEFAULT_DEMO_DB,
    database_id: str = "concert_singer",
    model_name: str = "template",
    checkpoint_path: Path | str | None = None,
) -> int:
    """Execute the scripted 3-case demonstration required by Part 2."""
    db_path = Path(db_path)
    if checkpoint_path is not None:
        checkpoint_path = Path(checkpoint_path)
    if not db_path.is_file():
        print(f"Error: Demo database file not found at {db_path}", file=sys.stderr)
        return 1

    models = ["template", "lstm"] if model_name == "both" else [model_name]
    schema = load_demo_schema(db_path, database_id)
    bar = "=" * 70
    print(_style(bar, "2"))
    print(_style(f"  TEXT-TO-SQL PART 2 DEMO   model: {' vs '.join(models)}", "1"))
    print(f"  Database : {database_id}")
    print(f"  Tables   : {', '.join(t.name for t in schema.tables)}")
    print("  Verdicts compare each query's result with the gold query's result (as EX does).")
    print(_style(bar, "2"))

    scores = {name: 0 for name in models}
    for case in SCRIPTED_DEMO_CASES:
        print()
        print(_style(f"--- {case.name} [{case.category.upper()}] ---", "1;35"))
        print(f'  Question: "{case.question}"')
        print(_style(f"  Tests   : {case.description}", "2"))
        if case.gold_sql:
            print(_style(f"  Gold SQL: {case.gold_sql}", "2"))
        for name in models:
            sql = predict_sql(case.question, schema, name, checkpoint_path)
            verdict, exec_result = judge(sql, db_path, case.gold_sql)
            scores[name] += verdict == "CORRECT"
            _print_prediction(name, sql, verdict, exec_result)

    print()
    print(_style(bar, "2"))
    print(_style("  SCORE (execution match on these 3 questions)", "1"))
    for name in models:
        print(f"    {name:<9}: {scores[name]}/{len(SCRIPTED_DEMO_CASES)}")
    print("  Full Spider test (2,147 questions): template EX 9.5%, LSTM EX 7.2%.")
    print(_style(bar, "2"))
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.train_demo:
        from .lstm.train_demo import run_training_demo

        return run_training_demo(
            databases=tuple(db.strip() for db in args.train_databases.split(",") if db.strip()),
            epochs=args.epochs,
        )

    db_path = args.database or DEFAULT_DEMO_DB
    if not db_path.is_file():
        print(
            f"Error: SQLite database not found at '{db_path}'. "
            f"Please specify --database <path/to/db.sqlite>.",
            file=sys.stderr,
        )
        return 1

    if args.demo:
        return run_scripted_demo(
            db_path=db_path,
            database_id=args.database_id if args.database_id != "demo-database" else db_path.stem,
            model_name=args.model,
            checkpoint_path=args.checkpoint,
        )

    if not args.question:
        print(
            "Error: --question is required when not running in --demo mode.",
            file=sys.stderr,
        )
        return 1

    database_id = args.database_id if args.database_id != "demo-database" else db_path.stem
    schema = load_demo_schema(db_path, database_id)
    if args.model == "both":
        print(f"Question: {args.question}")
        for name in ("template", "lstm"):
            sql = predict_sql(args.question, schema, name, args.checkpoint)
            verdict, exec_result = judge(sql, db_path, None)
            _print_prediction(name, sql, verdict, exec_result)
        return 0
    sql, success, display = run_query(
        args.question,
        schema,
        db_path,
        model_name=args.model,
        checkpoint_path=args.checkpoint,
    )
    print(f"Question     : {args.question}")
    print(f"Generated SQL: {sql if sql else '(none)'}")
    print(f"Status       : {'SUCCESS' if success else 'FAILURE'}")
    print("Result:")
    print(display)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
