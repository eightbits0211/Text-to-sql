import json
import sqlite3
from pathlib import Path

from text_to_sql.baselines.template import TemplateBaseline
from text_to_sql.data.contracts import (
    DatasetSplit,
    ExampleRecord,
    QueryDifficulty,
    QueryStructure,
)
from text_to_sql.data.schema import ColumnSpec, DatabaseSchema, TableSpec
from text_to_sql.evaluation.artifacts import write_prediction_artifacts


def _schema() -> DatabaseSchema:
    return DatabaseSchema(
        "shop",
        (
            TableSpec(
                "customers",
                (ColumnSpec("id", "INTEGER", True), ColumnSpec("name", "TEXT")),
            ),
        ),
    )


def _example(database_path: Path) -> ExampleRecord:
    return ExampleRecord(
        example_id="shop-0",
        dataset="fixture",
        split=DatasetSplit.DEV,
        database_id="shop",
        database_path=database_path,
        question="How many customers are there?",
        schema_text="database: shop\ntable: customers\ncolumns:\n  - id [INTEGER]\n  - name [TEXT]",
        gold_sql='SELECT COUNT(*) FROM "customers"',
        difficulty=QueryDifficulty.EASY,
        query_structure=QueryStructure.SINGLE_TABLE,
    )


def test_template_baseline_selects_table_and_count() -> None:
    baseline = TemplateBaseline()

    assert baseline.predict("How many customers are there?", _schema()) == (
        'SELECT COUNT(*) FROM "customers"'
    )


def test_template_baseline_evaluates_and_writes_jsonl(tmp_path: Path) -> None:
    database_path = tmp_path / "shop.sqlite"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT)")
        connection.executemany("INSERT INTO customers(name) VALUES (?)", [("Ada",), ("Lin",)])
        connection.commit()
    finally:
        connection.close()

    example = _example(database_path)
    baseline = TemplateBaseline()
    report = baseline.evaluate((example,))
    artifact_path = tmp_path / "artifacts" / "predictions.jsonl"
    written = write_prediction_artifacts(
        artifact_path,
        (example,),
        baseline.predict_records((example,)),
    )

    assert report.execution_accuracy == 1.0
    assert written == 1
    assert json.loads(artifact_path.read_text(encoding="utf-8"))["model_name"] == (
        "template-baseline"
    )
