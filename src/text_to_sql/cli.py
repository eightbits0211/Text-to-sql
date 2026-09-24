"""Command-line demo and scripted rehearsal for Part 2 Text-to-SQL baselines."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from .baselines.template import TemplateBaseline
from .data.schema import DatabaseSchema
from .data.sqlite_schema import load_sqlite_schema
from .evaluation.metrics import execute_read_only

DEFAULT_DEMO_DB = Path(
    "/Users/roshini/datasets/text-to-sql/spider/spider_data/database/concert_singer/concert_singer.sqlite"
)
DEFAULT_CHECKPOINT = Path(
    "/Users/roshini/datasets/text-to-sql/artifacts-lstm-gpu-run/lstm-checkpoint/lstm_smoke.pt"
)


@dataclass(frozen=True)
class DemoCase:
    name: str
    category: str
    question: str
    description: str


SCRIPTED_DEMO_CASES: tuple[DemoCase, ...] = (
    DemoCase(
        name="Case 1 (Easy Projection)",
        category="easy",
        question="What are the names of all singers from France?",
        description="Tests single-table schema resolution, column projection, and string equality condition.",
    ),
    DemoCase(
        name="Case 2 (Numeric Filter)",
        category="filter",
        question="What are the names and ages of singers older than 30?",
        description="Tests multi-column projection and numeric comparison filtering (> 30).",
    ),
    DemoCase(
        name="Case 3 (Complex / Failure Case)",
        category="failure_case",
        question="What is the stadium name and capacity for the concert with the highest attendance?",
        description="Demonstrates explicit unsupported/error handling when cross-table joins or unsupported constructs are requested.",
    ),
)


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
        choices=["template", "lstm"],
        default="template",
        help="Baseline model to use (default: template).",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help="Path to LSTM model checkpoint if using --model lstm.",
    )
    return parser


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


def run_query(
    question: str,
    schema: DatabaseSchema,
    db_path: Path | str,
    model_name: str = "template",
    checkpoint_path: Path | str | None = None,
) -> tuple[str, bool, str]:
    """Generate SQL, validate, and execute. Returns (sql, is_success, output_display)."""
    db_path = Path(db_path)
    if checkpoint_path is not None:
        checkpoint_path = Path(checkpoint_path)
    if model_name == "template":
        baseline = TemplateBaseline()
        sql = baseline.predict(question, schema)
    elif model_name == "lstm":
        from .lstm.adapter import LSTMBaseline

        target_ckpt = checkpoint_path or DEFAULT_CHECKPOINT
        if target_ckpt is not None and Path(target_ckpt).is_file():
            baseline = LSTMBaseline.from_checkpoint(Path(target_ckpt))
        else:
            baseline = LSTMBaseline()
        db_id = getattr(schema, "database_id", "unknown")
        sql = baseline.predict(question, schema, database_id=db_id)
    else:
        raise ValueError(f"Unsupported model: {model_name}")

    if not sql or not sql.strip():
        return (
            "",
            False,
            "UNSUPPORTED: Model emitted empty SQL (query structure is outside supported grammar).",
        )

    exec_result = execute_read_only(sql, db_path)
    if exec_result.status != "success":
        return (sql, False, f"EXECUTION ERROR: {exec_result.error}")

    table_str = format_table(exec_result.columns, exec_result.rows)
    row_count = len(exec_result.rows)
    return (sql, True, f"{table_str}\n({row_count} row{'s' if row_count != 1 else ''} returned)")


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

    schema = load_sqlite_schema(db_path, database_id)
    print("=" * 70)
    print(f"  TEXT-TO-SQL PART 2 LIVE DEMO SHOWCASE (Model: {model_name})")
    print(f"  Database: {database_id} ({db_path})")
    print("  Schema Tables:", ", ".join(t.name for t in schema.tables))
    print("=" * 70)

    for case in SCRIPTED_DEMO_CASES:
        print(f"\n--- {case.name} [{case.category.upper()}] ---")
        print(f"Purpose : {case.description}")
        print(f'Question: "{case.question}"')
        sql, success, display = run_query(
            case.question,
            schema,
            db_path,
            model_name=model_name,
            checkpoint_path=checkpoint_path,
        )
        print(f"Generated SQL: {sql if sql else '(empty)'}")
        print(f"Status       : {'SUCCESS' if success else 'RECORDED FAILURE / UNSUPPORTED'}")
        print("Result:")
        for line in display.splitlines():
            print(f"  {line}")

    print("\n" + "=" * 70)
    print("  DEMO SHOWCASE COMPLETE: All 3 cases evaluated gracefully.")
    print("=" * 70)
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

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

    schema = load_sqlite_schema(db_path, args.database_id)
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
