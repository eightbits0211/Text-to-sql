import json
import sqlite3
from pathlib import Path

from text_to_sql.data.contracts import DatasetSplit, ExclusionReason
from text_to_sql.data.wikisql import load_wikisql


def _create_database(database_root: Path) -> None:
    connection = sqlite3.connect(database_root / "people.db")
    try:
        connection.execute("CREATE TABLE people (id INTEGER PRIMARY KEY, name TEXT)")
        connection.executemany(
            "INSERT INTO people (id, name) VALUES (?, ?)",
            [(1, "Ada"), (2, "Grace")],
        )
        connection.commit()
    finally:
        connection.close()


def test_load_wikisql_reconstructs_structured_sql_and_statistics(tmp_path: Path) -> None:
    _create_database(tmp_path)
    source_path = tmp_path / "train.json"
    source_path.write_text(
        json.dumps(
            [
                {
                    "question": "What is the name for id 1?",
                    "table": {"id": "people", "header": ["id", "name"]},
                    "sql": {"sel": 1, "agg": 0, "conds": [[0, "=", 1]]},
                }
            ]
        ),
        encoding="utf-8",
    )

    result = load_wikisql(source_path, tmp_path, split=DatasetSplit.TRAIN)

    assert len(result.records) == 1
    assert result.records[0].gold_sql == 'SELECT "name" FROM "people" WHERE "id" = 1'
    assert result.records[0].schema_text.startswith("database: people")
    assert result.statistics.retained_examples == 1
    assert result.statistics.splits[0].database_count == 1


def test_load_wikisql_records_exclusions_without_aborting(tmp_path: Path) -> None:
    source_path = tmp_path / "train.json"
    source_path.write_text(
        json.dumps(
            [
                {"question": "", "table": {"id": "people", "header": ["id"]}},
                {
                    "question": "Uses a missing database",
                    "table": {"id": "missing", "header": ["id"]},
                    "sql": {"query": "SELECT id FROM missing"},
                },
            ]
        ),
        encoding="utf-8",
    )

    result = load_wikisql(source_path, tmp_path, split=DatasetSplit.TRAIN)

    assert not result.records
    assert result.statistics.excluded_examples == 2
    assert [event.reason for event in result.exclusions] == [
        ExclusionReason.MISSING_QUESTION,
        ExclusionReason.DATABASE_NOT_FOUND,
    ]


def test_load_wikisql_rejects_join_query(tmp_path: Path) -> None:
    source_path = tmp_path / "train.json"
    source_path.write_text(
        json.dumps(
            [
                {
                    "question": "Join two tables",
                    "table": {"id": "people", "header": ["id"]},
                    "sql": {
                        "query": "SELECT p.id FROM people p JOIN visits v ON p.id = v.person_id"
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    result = load_wikisql(source_path, tmp_path, split=DatasetSplit.TRAIN)

    assert result.exclusions[0].reason is ExclusionReason.UNSUPPORTED_QUERY_STRUCTURE
