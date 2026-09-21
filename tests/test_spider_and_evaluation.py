import json
import sqlite3
from pathlib import Path

from text_to_sql.data.contracts import DatasetSplit
from text_to_sql.data.spider import load_spider
from text_to_sql.evaluation.metrics import Prediction, evaluate_predictions


def _create_spider_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    database_root = tmp_path / "databases" / "shop"
    database_root.mkdir(parents=True)
    database_path = database_root / "shop.sqlite"
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(
            """
            CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER);
            INSERT INTO customers VALUES (1, 'Ada');
            INSERT INTO orders VALUES (10, 1);
            """
        )
        connection.commit()
    finally:
        connection.close()
    source_path = tmp_path / "dev.json"
    source_path.write_text(
        json.dumps(
            [
                {
                    "db_id": "shop",
                    "question": "Which customer has an order?",
                    "query": "SELECT customers.name FROM customers JOIN orders ON customers.id = orders.customer_id",
                    "hardness": "medium",
                },
                {"db_id": "missing", "question": "Missing", "query": "SELECT 1", "hardness": "easy"},
            ]
        ),
        encoding="utf-8",
    )
    schema_path = tmp_path / "tables.json"
    schema_path.write_text(
        json.dumps(
            [
                {
                    "db_id": "shop",
                    "table_names_original": ["customers", "orders"],
                    "column_names_original": [
                        [-1, "*"],
                        [0, "id"],
                        [0, "name"],
                        [1, "id"],
                        [1, "customer_id"],
                    ],
                    "column_types": ["text", "number", "text", "number", "number"],
                    "primary_keys": [1, 3],
                    "foreign_keys": [[4, 1]],
                },
                {
                    "db_id": "missing",
                    "table_names_original": ["missing_table"],
                    "column_names_original": [[-1, "*"], [0, "id"]],
                    "column_types": ["text", "number"],
                    "primary_keys": [1],
                    "foreign_keys": [],
                },
            ]
        ),
        encoding="utf-8",
    )
    return source_path, schema_path, tmp_path / "databases"


def test_spider_loader_retains_join_and_reports_missing_database(tmp_path: Path) -> None:
    source_path, schema_path, database_root = _create_spider_fixture(tmp_path)

    result = load_spider(
        source_path,
        schema_path,
        database_root,
        split=DatasetSplit.DEV,
    )

    assert len(result.records) == 1
    assert result.records[0].difficulty.value == "medium"
    assert result.records[0].query_structure.value == "multi_table_join"
    assert "customers.id -> orders.id" not in result.records[0].schema_text
    assert result.statistics.exclusions_by_reason == {"database_not_found": 1}


def test_evaluation_reports_exact_execution_and_invalid_sql(tmp_path: Path) -> None:
    source_path, schema_path, database_root = _create_spider_fixture(tmp_path)
    loaded = load_spider(source_path, schema_path, database_root, split=DatasetSplit.DEV)
    example = loaded.records[0]
    predictions = (
        Prediction(
            example_id=example.example_id,
            model_name="fixture",
            predicted_sql=example.gold_sql,
        ),
    )

    report = evaluate_predictions((example,), predictions)

    assert report.exact_match_accuracy == 1.0
    assert report.execution_accuracy == 1.0
    assert report.invalid_sql_rate == 0.0


def test_evaluation_counts_missing_prediction_as_invalid(tmp_path: Path) -> None:
    source_path, schema_path, database_root = _create_spider_fixture(tmp_path)
    loaded = load_spider(source_path, schema_path, database_root, split=DatasetSplit.DEV)

    report = evaluate_predictions(loaded.records, ())

    assert report.evaluated_count == 1
    assert report.invalid_sql_rate == 1.0
    assert report.examples[0].failure_category == "empty_prediction"
