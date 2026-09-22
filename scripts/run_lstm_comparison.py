"""Compare TemplateBaseline vs LSTMBaseline on 200-example WikiSQL and Spider dev slices.

Usage:
    uv run python scripts/run_lstm_comparison.py [--smoke-limit N]

All paths are read from the same environment variables as run_part2_smoke.py.
Falls back to hardcoded local dataset paths if env vars are not set.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import torch

from text_to_sql.baselines import TemplateBaseline
from text_to_sql.config import Part2Config
from text_to_sql.data.contracts import DatasetSplit
from text_to_sql.data.spider import load_spider
from text_to_sql.data.wikisql import load_wikisql
from text_to_sql.evaluation.artifacts import write_prediction_artifacts
from text_to_sql.evaluation.reports import write_evaluation_reports
from text_to_sql.lstm.adapter import LSTMBaseline
from text_to_sql.lstm.training import TrainingConfig

# Fallback paths — used when environment variables are not set
_WIKISQL_ROOT = Path("/Users/roshini/datasets/text-to-sql/wikisql/data")
_SPIDER_ROOT = Path("/Users/roshini/datasets/text-to-sql/spider/spider_data")

_DEFAULT_ARTIFACT_DIR = Path("/Users/roshini/datasets/text-to-sql/artifacts-lstm-comparison")


def _build_config(smoke_limit: int | None = None) -> Part2Config:
    """Try env vars first; fall back to hardcoded local paths. 0 or None means full split."""
    import os

    wikisql_source = os.environ.get("TEXT2SQL_WIKISQL_SOURCE")
    wikisql_db_root = os.environ.get("TEXT2SQL_WIKISQL_DATABASE_ROOT")
    spider_source = os.environ.get("TEXT2SQL_SPIDER_SOURCE")
    spider_schema = os.environ.get("TEXT2SQL_SPIDER_SCHEMA")
    spider_db_root = os.environ.get("TEXT2SQL_SPIDER_DATABASE_ROOT")
    artifact_dir = os.environ.get("TEXT2SQL_ARTIFACT_DIRECTORY")

    # If smoke_limit is 0 or None, treat as full evaluation (no slicing)
    effective_limit = None if (smoke_limit is None or smoke_limit <= 0) else smoke_limit

    return Part2Config(
        wikisql_source=Path(wikisql_source) if wikisql_source else _WIKISQL_ROOT / "dev.jsonl",
        wikisql_database_root=Path(wikisql_db_root) if wikisql_db_root else _WIKISQL_ROOT,
        spider_source=Path(spider_source) if spider_source else _SPIDER_ROOT / "dev.json",
        spider_schema=Path(spider_schema) if spider_schema else _SPIDER_ROOT / "tables.json",
        spider_database_root=Path(spider_db_root) if spider_db_root else _SPIDER_ROOT / "database",
        artifact_directory=Path(artifact_dir) if artifact_dir else _DEFAULT_ARTIFACT_DIR,
        smoke_limit=effective_limit,
    )


def _load_wikisql(config: Part2Config) -> object:
    return load_wikisql(
        config.wikisql_source,
        config.wikisql_database_root,
        split=DatasetSplit.DEV,
        database_pattern="dev.db",
        table_metadata_path=config.wikisql_source.with_name("dev.tables.jsonl"),
        smoke_limit=config.smoke_limit,
    )


def _load_spider(config: Part2Config) -> object:
    return load_spider(
        config.spider_source,
        config.spider_schema,
        config.spider_database_root,
        split=DatasetSplit.DEV,
        smoke_limit=config.smoke_limit,
    )


def _run_baseline(name: str, baseline: object, records: tuple, output_dir: Path) -> dict:
    """Run evaluate + write artifacts for one baseline."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report = baseline.evaluate(records)
    write_prediction_artifacts(
        output_dir / "predictions.jsonl",
        records,
        baseline.predict_records(records),
    )
    write_evaluation_reports(output_dir, report, records)
    return {
        "model": name,
        "retained_examples": len(records),
        "execution_accuracy": report.execution_accuracy,
        "exact_match_accuracy": report.exact_match_accuracy,
        "invalid_sql_rate": report.invalid_sql_rate,
        "artifact_directory": str(output_dir),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-limit", type=int, default=200,
                        help="Max examples to evaluate from dev splits (0 for full evaluation; default: 200)")
    parser.add_argument("--full-eval", action="store_true", default=False,
                        help="Evaluate on complete dev splits (all 8,415 WikiSQL and 1,034 Spider records)")
    parser.add_argument("--epochs", type=int, default=5,
                        help="LSTM training epochs on the train slice")
    parser.add_argument("--train-limit", type=int, default=200,
                        help="Max WikiSQL train examples for LSTM fitting (e.g. 56000 for full split)")
    parser.add_argument("--batch-size", type=int, default=32,
                        help="Minibatch size for LSTM training (default: 32)")
    parser.add_argument("--device", default=None,
                        help="Compute device (cuda or cpu). Defaults to cuda if available.")
    args = parser.parse_args()

    selected_device = (
        torch.device(args.device)
        if args.device
        else (torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu"))
    )

    eval_limit = None if args.full_eval or args.smoke_limit <= 0 else args.smoke_limit
    config = _build_config(smoke_limit=eval_limit)
    config.validate()

    eval_label = "FULL DATASET" if eval_limit is None else f"limit={eval_limit}"
    print(f"\n{'='*60}")
    print(f"  LSTM vs Template comparison  ({eval_label})")
    print(f"  Device: {selected_device} | Batch size: {args.batch_size}")
    print(f"{'='*60}\n")

    # ----------------------------------------------------------------
    # Load dev slices
    # ----------------------------------------------------------------
    print("Loading WikiSQL dev slice...")
    wikisql_dev = _load_wikisql(config)
    print(f"  retained={len(wikisql_dev.records)}  excluded={len(wikisql_dev.exclusions)}")

    print("Loading Spider dev slice...")
    spider_dev = _load_spider(config)
    print(f"  retained={len(spider_dev.records)}  excluded={len(spider_dev.exclusions)}")

    # ----------------------------------------------------------------
    # Fit LSTM on WikiSQL train slice
    # ----------------------------------------------------------------
    print(f"\nFitting LSTM on up to {args.train_limit} WikiSQL train examples "
          f"({args.epochs} epochs) on {selected_device}...")
    wikisql_train = load_wikisql(
        config.wikisql_source.with_name("train.jsonl"),
        config.wikisql_database_root,
        split=DatasetSplit.TRAIN,
        database_pattern="train.db",
        table_metadata_path=config.wikisql_source.with_name("train.tables.jsonl"),
        smoke_limit=args.train_limit,
    )
    print(f"  train retained={len(wikisql_train.records)}")

    lstm_checkpoint_dir = config.artifact_directory / "lstm-checkpoint"
    lstm_cfg = TrainingConfig(
        max_epochs=args.epochs,
        batch_size=args.batch_size,
        smoke_limit=args.train_limit,
        seed=42,
    )
    lstm_baseline = LSTMBaseline(config=lstm_cfg, device=selected_device)
    lstm_baseline.fit(wikisql_train.records, checkpoint_dir=lstm_checkpoint_dir)
    print("  LSTM fitting complete.")

    # ----------------------------------------------------------------
    # Evaluate both baselines on both dev splits
    # ----------------------------------------------------------------
    template = TemplateBaseline()
    results = []

    for dataset, result in (("wikisql", wikisql_dev), ("spider", spider_dev)):
        print(f"\n--- {dataset.upper()} ({len(result.records)} examples) ---")
        for model_name, baseline in (("template", template), ("lstm", lstm_baseline)):
            out_dir = config.artifact_directory / dataset / model_name
            row = _run_baseline(model_name, baseline, result.records, out_dir)
            results.append({"dataset": dataset, **row})
            print(
                f"  {model_name:12s}  exec_acc={row['execution_accuracy']:.4f}  "
                f"exact={row['exact_match_accuracy']:.4f}  "
                f"invalid={row['invalid_sql_rate']:.4f}"
            )

    # ----------------------------------------------------------------
    # Write comparison manifest
    # ----------------------------------------------------------------
    manifest = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "smoke_limit": args.smoke_limit,
        "train_limit": args.train_limit,
        "lstm_epochs": args.epochs,
        "results": results,
    }
    manifest_path = config.artifact_directory / "comparison_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest written → {manifest_path}")

    # ----------------------------------------------------------------
    # Side-by-side summary
    # ----------------------------------------------------------------
    print(f"\n{'='*60}")
    print("  COMPARISON SUMMARY")
    print(f"{'='*60}")
    print(f"{'Dataset':<10} {'Model':<12} {'Exec Acc':>10} {'Exact':>8} {'Invalid':>9}")
    print("-" * 55)
    for row in results:
        print(
            f"{row['dataset']:<10} {row['model']:<12} "
            f"{row['execution_accuracy']:>10.4f} "
            f"{row['exact_match_accuracy']:>8.4f} "
            f"{row['invalid_sql_rate']:>9.4f}"
        )
    print(f"{'='*60}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
