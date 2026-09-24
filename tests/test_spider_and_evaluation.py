import json
import sqlite3
from dataclasses import replace
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
                    "sql": {
                        "from": {
                            "table_units": [["table_unit", 0], ["table_unit", 1]],
                            "conds": [],
                        },
                        "select": [False, [[0, [0, [0, 2, False], None]]]],
                        "where": [],
                        "groupBy": [],
                        "having": [],
                        "orderBy": [],
                        "limit": None,
                        "intersect": None,
                        "union": None,
                        "except": None,
                    },
                },
                {
                    "db_id": "missing",
                    "question": "Missing",
                    "query": "SELECT 1",
                    "sql": {
                        "from": {"table_units": [["table_unit", 0]], "conds": []},
                        "select": [False, [[0, [0, [0, 1, False], None]]]],
                        "where": [],
                        "groupBy": [],
                        "having": [],
                        "orderBy": [],
                        "limit": None,
                        "intersect": None,
                        "union": None,
                        "except": None,
                    },
                },
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
    assert result.records[0].difficulty.value == "easy"
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


def test_execution_accuracy_ignores_sql_alias_case(tmp_path: Path) -> None:
    source_path, schema_path, database_root = _create_spider_fixture(tmp_path)
    loaded = load_spider(source_path, schema_path, database_root, split=DatasetSplit.DEV)
    example = replace(loaded.records[0], gold_sql="SELECT count(*) FROM customers")
    prediction = Prediction(
        example_id=example.example_id,
        model_name="fixture",
        predicted_sql='SELECT COUNT(*) FROM "customers"',
    )

    report = evaluate_predictions((example,), (prediction,))

    assert report.execution_accuracy == 1.0


def test_evaluation_counts_missing_prediction_as_invalid(tmp_path: Path) -> None:
    source_path, schema_path, database_root = _create_spider_fixture(tmp_path)
    loaded = load_spider(source_path, schema_path, database_root, split=DatasetSplit.DEV)

    report = evaluate_predictions(loaded.records, ())

    assert report.evaluated_count == 1
    assert report.invalid_sql_rate == 1.0
    assert report.examples[0].failure_category == "empty_prediction"


# ---------------------------------------------------------------------------
# Spider difficulty classification tests
# ---------------------------------------------------------------------------

from text_to_sql.data.contracts import QueryDifficulty
from text_to_sql.data.spider import _classify_difficulty


def _make_sql(
    *,
    n_tables: int = 1,
    n_select: int = 1,
    has_where: bool = False,
    n_where: int = 0,
    has_group: bool = False,
    has_order: bool = False,
    has_limit: bool = False,
    has_intersect: bool = False,
    has_union: bool = False,
    has_except: bool = False,
    has_or: bool = False,
    has_like: bool = False,
    agg_indices: tuple[int, ...] = (),
) -> dict:
    """Build a minimal Spider-format parsed SQL dict for difficulty testing."""
    table_units = [["table_unit", i] for i in range(n_tables)]
    select_items = []
    for i in range(n_select):
        agg_op = 3 if i in agg_indices else 0  # 3 = COUNT
        select_items.append([agg_op, [0, [0, i + 1, False], None]])

    where: list = []
    for j in range(n_where):
        op = 9 if (has_like and j == 0) else 2  # 9 = LIKE, 2 = =
        cond = [False, op, [0, [0, j + 1, False], None], f"val{j}", None]
        if where:
            where.append("or" if has_or else "and")
        where.append(cond)

    return {
        "from": {"table_units": table_units, "conds": []},
        "select": [False, select_items],
        "where": where,
        "groupBy": [[0, [0, 1, False]]] if has_group else [],
        "having": [],
        "orderBy": ["asc", [[0, [0, 1, False]]]] if has_order else [],
        "limit": 5 if has_limit else None,
        "intersect": {
            "select": [False, [[0, [0, [0, 1, False], None]]]],
            "from": {"table_units": [["table_unit", 0]], "conds": []},
            "where": [],
            "groupBy": [],
            "having": [],
            "orderBy": [],
            "limit": None,
            "intersect": None,
            "union": None,
            "except": None,
        }
        if has_intersect
        else None,
        "union": {
            "select": [False, [[0, [0, [0, 1, False], None]]]],
            "from": {"table_units": [["table_unit", 0]], "conds": []},
            "where": [],
            "groupBy": [],
            "having": [],
            "orderBy": [],
            "limit": None,
            "intersect": None,
            "union": None,
            "except": None,
        }
        if has_union
        else None,
        "except": {
            "select": [False, [[0, [0, [0, 1, False], None]]]],
            "from": {"table_units": [["table_unit", 0]], "conds": []},
            "where": [],
            "groupBy": [],
            "having": [],
            "orderBy": [],
            "limit": None,
            "intersect": None,
            "union": None,
            "except": None,
        }
        if has_except
        else None,
    }


def test_classify_difficulty_easy() -> None:
    """SELECT col FROM t → easy (comp1=0, comp2=0, others=0)."""
    sql = _make_sql(n_tables=1, n_select=1)
    assert _classify_difficulty(sql) == QueryDifficulty.EASY


def test_classify_difficulty_medium() -> None:
    """SELECT col1, col2 FROM t WHERE c1 = v → medium (comp1=1, comp2=0, others=1)."""
    sql = _make_sql(n_tables=1, n_select=2, has_where=True, n_where=1)
    assert _classify_difficulty(sql) == QueryDifficulty.MEDIUM


def test_classify_difficulty_hard() -> None:
    """SELECT col1, col2 FROM t1 JOIN t2 WHERE c=v GROUP BY col → hard."""
    sql = _make_sql(n_tables=2, n_select=2, has_where=True, n_where=1, has_group=True)
    assert _classify_difficulty(sql) == QueryDifficulty.HARD


def test_classify_difficulty_extra_hard() -> None:
    """Query with INTERSECT and multiple components → extra-hard."""
    sql = _make_sql(
        n_tables=2, n_select=2, has_where=True, n_where=2, has_group=True, has_intersect=True
    )
    assert _classify_difficulty(sql) == QueryDifficulty.EXTRA_HARD


def test_classify_difficulty_unknown_for_missing_sql() -> None:
    """No parsed SQL dict → UNKNOWN."""
    assert _classify_difficulty(None) == QueryDifficulty.UNKNOWN
    assert _classify_difficulty({}) == QueryDifficulty.UNKNOWN
