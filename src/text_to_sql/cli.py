"""Command-line demo for the deterministic baseline."""

import argparse
from pathlib import Path

from .baselines.template import TemplateBaseline
from .data.sqlite_schema import load_sqlite_schema
from .evaluation.metrics import execute_read_only


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate SQL from a question and SQLite schema.")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--database-id", default="cli-database")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    schema = load_sqlite_schema(args.database, args.database_id)
    sql = TemplateBaseline().predict(args.question, schema)
    result = execute_read_only(sql, args.database)
    print(f"SQL: {sql}")
    if result.status != "success":
        print(f"ERROR: {result.error}")
        return 1
    print(" | ".join(result.columns))
    for row in result.rows:
        print(" | ".join(str(value) for value in row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
