"""Score Spider predictions with the official evaluator (taoyds/test-suite-sql-eval).

The evaluator is an external tool kept outside this repository. It reports
exact-set-match accuracy (the official, component-wise "EM") and execution
accuracy by hardness tier. Pass a test-suite database directory as ``--db`` to
obtain test-suite accuracy; the plain Spider databases give standard EX.

Usage:
    uv run python scripts/run_official_spider_eval.py \
        --predictions artifacts/.../spider/lstm/predictions.jsonl \
        --split dev --output-dir artifacts/.../spider/lstm/official
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

_TOOLS = Path("/Users/roshini/datasets/text-to-sql/tools")
_SPIDER = Path("/Users/roshini/datasets/text-to-sql/spider/spider_data")
_LEVELS = ("easy", "medium", "hard", "extra", "all")


def _one_line(sql: str) -> str:
    text = re.sub(r"\s+", " ", sql).strip()
    return text or "SELECT"


_QUOTED_IDENTIFIER = re.compile(r'"([A-Za-z_][A-Za-z0-9_]*)"')


def strip_identifier_quotes(sql: str) -> str:
    """Unquote "Identifier" tokens; the official parser reads them as string values."""
    return _QUOTED_IDENTIFIER.sub(r"\1", sql)


def write_eval_files(
    predictions_path: Path, output_dir: Path, unquote_identifiers: bool = False
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(line) for line in predictions_path.read_text(encoding="utf-8").splitlines()]
    gold_path = output_dir / "gold.txt"
    pred_path = output_dir / "pred.txt"
    gold_path.write_text(
        "".join(f"{_one_line(row['gold_sql'])}\t{row['database_id']}\n" for row in rows),
        encoding="utf-8",
    )
    pred_path.write_text(
        "".join(
            f"{_one_line(_maybe_unquote(row['predicted_sql'], unquote_identifiers))}\n"
            for row in rows
        ),
        encoding="utf-8",
    )
    return gold_path, pred_path


def _maybe_unquote(sql: str, enabled: bool) -> str:
    return strip_identifier_quotes(sql) if enabled else sql


def parse_scores(stdout: str) -> dict[str, dict[str, float]]:
    """Parse the evaluator's 'count'/'execution'/'exact match' summary rows."""
    scores: dict[str, dict[str, float]] = {}
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) == len(_LEVELS) + 1 and parts[0] == "count":
            scores["count"] = dict(zip(_LEVELS, map(float, parts[1:]), strict=True))
        elif len(parts) == len(_LEVELS) + 1 and parts[0] == "execution":
            scores["execution"] = dict(zip(_LEVELS, map(float, parts[1:]), strict=True))
        elif len(parts) == len(_LEVELS) + 2 and parts[:2] == ["exact", "match"]:
            scores["exact_set_match"] = dict(zip(_LEVELS, map(float, parts[2:]), strict=True))
    return scores


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--db", type=Path, default=None, help="Database directory override")
    parser.add_argument("--evaluator", type=Path, default=_TOOLS / "test-suite-sql-eval")
    parser.add_argument("--python", type=Path, default=_TOOLS / "evalenv" / "bin" / "python")
    parser.add_argument(
        "--unquote-identifiers",
        action="store_true",
        help='Diagnostic: rewrite "Identifier" as Identifier before scoring (template output)',
    )
    args = parser.parse_args()

    database_dir = args.db or (_SPIDER / ("database" if args.split == "dev" else "test_database"))
    table_path = _SPIDER / ("tables.json" if args.split == "dev" else "test_tables.json")
    gold_path, pred_path = write_eval_files(
        args.predictions, args.output_dir, args.unquote_identifiers
    )
    completed = subprocess.run(
        [
            str(args.python),
            "evaluation.py",
            "--gold",
            str(gold_path.resolve()),
            "--pred",
            str(pred_path.resolve()),
            "--db",
            str(database_dir),
            "--table",
            str(table_path),
            "--etype",
            "all",
        ],
        cwd=args.evaluator,
        capture_output=True,
        text=True,
        check=False,
    )
    (args.output_dir / "official_eval.txt").write_text(
        completed.stdout + completed.stderr, encoding="utf-8"
    )
    if completed.returncode != 0:
        print(completed.stderr[-2000:])
        return completed.returncode
    scores = parse_scores(completed.stdout)
    per_example = args.output_dir / "official_per_example.jsonl"
    subprocess.run(
        [
            str(args.python),
            str(Path(__file__).resolve().parent / "official_per_example.py"),
            str(gold_path.resolve()),
            str(args.output_dir.resolve() / "pred.txt"),
            str(database_dir),
            str(table_path),
            str(per_example.resolve()),
        ],
        cwd=args.evaluator,
        check=True,
        capture_output=True,
    )
    payload = {
        "split": args.split,
        "database_dir": str(database_dir),
        "unquote_identifiers": args.unquote_identifiers,
        "scores": scores,
    }
    (args.output_dir / "official_scores.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    print(json.dumps(scores, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
