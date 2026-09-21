"""Run bounded WikiSQL and Spider loading with the deterministic baseline."""

import argparse
from dataclasses import replace

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
    args = parser.parse_args()

    config = Part2Config.from_environment()
    if args.smoke_limit is not None:
        config = replace(config, smoke_limit=args.smoke_limit)
    config.validate()

    baseline = TemplateBaseline()
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
        print(
            f"{dataset}: retained={len(result.records)} "
            f"excluded={len(result.exclusions)} "
            f"execution_accuracy={report.execution_accuracy:.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
