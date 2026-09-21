"""Run bounded WikiSQL and Spider loading with the deterministic baseline."""

import argparse
import hashlib
import json
import subprocess
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from text_to_sql.baselines import TemplateBaseline
from text_to_sql.config import Part2Config
from text_to_sql.data.contracts import DatasetSplit
from text_to_sql.data.spider import load_spider
from text_to_sql.data.wikisql import load_wikisql
from text_to_sql.evaluation.artifacts import write_prediction_artifacts
from text_to_sql.evaluation.reports import write_evaluation_reports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-limit", type=int, default=None)
    parser.add_argument(
        "--full-dev",
        action="store_true",
        help="evaluate every example in the configured development split",
    )
    args = parser.parse_args()

    config = Part2Config.from_environment()
    if args.full_dev:
        config = replace(config, smoke_limit=None)
    elif args.smoke_limit is not None:
        config = replace(config, smoke_limit=args.smoke_limit)
    config.validate()

    baseline = TemplateBaseline()
    run_records: list[dict[str, object]] = []
    for dataset, result in (
        (
            "wikisql",
            load_wikisql(
                config.wikisql_source,
                config.wikisql_database_root,
                split=DatasetSplit.DEV,
                database_pattern="dev.db",
                table_metadata_path=config.wikisql_source.with_name("dev.tables.jsonl"),
                smoke_limit=config.smoke_limit,
            ),
        ),
        (
            "spider",
            load_spider(
                config.spider_source,
                config.spider_schema,
                config.spider_database_root,
                split=DatasetSplit.DEV,
                smoke_limit=config.smoke_limit,
            ),
        ),
    ):
        report = baseline.evaluate(result.records)
        output_directory = config.artifact_directory / dataset
        write_prediction_artifacts(
            output_directory / "predictions.jsonl",
            result.records,
            baseline.predict_records(result.records),
        )
        write_evaluation_reports(output_directory, report, result.records)
        run_records.append(
            {
                "dataset": dataset,
                "retained_examples": len(result.records),
                "excluded_examples": len(result.exclusions),
                "execution_accuracy": report.execution_accuracy,
                "exact_match_accuracy": report.exact_match_accuracy,
                "invalid_sql_rate": report.invalid_sql_rate,
                "artifact_directory": str(output_directory),
            }
        )
        print(
            f"{dataset}: retained={len(result.records)} "
            f"excluded={len(result.exclusions)} "
            f"execution_accuracy={report.execution_accuracy:.4f}"
        )
    _write_run_manifest(config, run_records)
    return 0


def _write_run_manifest(config: Part2Config, dataset_results: list[dict[str, object]]) -> None:
    manifest = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "command": "uv run python scripts/run_part2_smoke.py",
        "model": TemplateBaseline.name,
        "configuration": {
            "smoke_limit": config.smoke_limit,
            "wikisql_source": str(config.wikisql_source),
            "wikisql_database_root": str(config.wikisql_database_root),
            "spider_source": str(config.spider_source),
            "spider_schema": str(config.spider_schema),
            "spider_database_root": str(config.spider_database_root),
            "artifact_directory": str(config.artifact_directory),
        },
        "source_sha256": {
            path_label: _sha256(path)
            for path_label, path in (
                ("wikisql_source", config.wikisql_source),
                ("spider_source", config.spider_source),
                ("spider_schema", config.spider_schema),
            )
        },
        "git_commit": _git_commit(),
        "datasets": dataset_results,
    }
    output_path = config.artifact_directory / "run-manifest.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"run_manifest={output_path}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
