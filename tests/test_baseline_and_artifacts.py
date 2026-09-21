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
from text_to_sql.evaluation.reports import write_evaluation_reports


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


def test_template_baseline_matches_plural_table_name() -> None:
    baseline = TemplateBaseline()

    assert baseline.predict("How many singers are there?", DatabaseSchema(
        "concert",
        (TableSpec("singer", (ColumnSpec("id", "INTEGER"),)), TableSpec("concert", (ColumnSpec("id", "INTEGER"),))),
    )) == 'SELECT COUNT(*) FROM "singer"'


def test_template_baseline_selects_projection_column() -> None:
    schema = DatabaseSchema(
        "people",
        (TableSpec("people", (
            ColumnSpec("id", "INTEGER"),
            ColumnSpec("full name", "TEXT"),
            ColumnSpec("age", "INTEGER"),
        )),),
    )

    assert TemplateBaseline().predict("What is the full name of each person?", schema) == (
        'SELECT "full name" FROM "people"'
    )


def test_template_baseline_prefers_name_over_identifier_for_name_question() -> None:
    schema = DatabaseSchema(
        "concert_singer",
        (TableSpec("singer", (
            ColumnSpec("Singer_ID", "INTEGER"),
            ColumnSpec("Name", "TEXT"),
            ColumnSpec("Country", "TEXT"),
        )),),
    )

    assert TemplateBaseline().predict("What are the names of all singers?", schema) == (
        'SELECT "Name" FROM "singer"'
    )


def test_template_baseline_extracts_numeric_condition() -> None:
    schema = DatabaseSchema(
        "people",
        (TableSpec("people", (
            ColumnSpec("name", "TEXT"),
            ColumnSpec("age", "INTEGER"),
        )),),
    )

    assert TemplateBaseline().predict(
        "Which name belongs to a person older than 30?", schema
    ) == 'SELECT "name" FROM "people" WHERE "age" > 30'


def test_template_baseline_extracts_string_and_multiple_conditions() -> None:
    schema = DatabaseSchema(
        "people",
        (TableSpec("people", (
            ColumnSpec("name", "TEXT"),
            ColumnSpec("country", "TEXT"),
            ColumnSpec("age", "INTEGER"),
        )),),
    )

    assert TemplateBaseline().predict(
        "List the name where country is India and age is at least 18.", schema
    ) == (
        'SELECT "name" FROM "people" WHERE "country" = \'India\' AND "age" >= 18'
    )


def test_template_baseline_aggregates_selected_column_with_condition() -> None:
    schema = DatabaseSchema(
        "people",
        (TableSpec("people", (
            ColumnSpec("name", "TEXT"),
            ColumnSpec("salary", "INTEGER"),
            ColumnSpec("country", "TEXT"),
        )),),
    )

    assert TemplateBaseline().predict(
        "What is the average salary for people from India?", schema
    ) == 'SELECT AVG("salary") FROM "people" WHERE "country" = \'India\''


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

    report_directory = tmp_path / "reports"
    write_evaluation_reports(report_directory, report, (example,))
    report_payload = json.loads(
        (report_directory / "evaluation.json").read_text(encoding="utf-8")
    )
    assert report_payload["breakdowns"]["difficulty"][0]["category"] == "easy"
    assert (report_directory / "breakdowns.csv").is_file()
    assert (report_directory / "evaluation.md").is_file()
