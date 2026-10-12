import sqlite3
from pathlib import Path
from unittest.mock import patch

from text_to_sql.cli import (
    SCRIPTED_DEMO_CASES,
    build_parser,
    format_table,
    main,
    run_query,
    run_scripted_demo,
)
from text_to_sql.data.sqlite_schema import load_sqlite_schema


def _create_sample_db(db_path: Path) -> None:
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "CREATE TABLE singer (Singer_ID INTEGER PRIMARY KEY, Name TEXT, Country TEXT, Age INTEGER)"
        )
        connection.executemany(
            "INSERT INTO singer (Singer_ID, Name, Country, Age) VALUES (?, ?, ?, ?)",
            [
                (1, "Alice Martin", "France", 28),
                (2, "Bob Smith", "United States", 35),
                (3, "Chloe Dubois", "France", 42),
            ],
        )
        connection.commit()
    finally:
        connection.close()


def test_build_parser_options() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["--database", "test.db", "--question", "Show names", "--model", "template"]
    )
    assert args.database == Path("test.db")
    assert args.question == "Show names"
    assert args.model == "template"
    assert not args.demo


def test_format_table_renders_ascii() -> None:
    rendered = format_table(("Name", "Age"), [("Alice", 28), ("Bob", 35)])
    assert "Alice" in rendered
    assert "Bob" in rendered
    assert "Name" in rendered
    assert "Age" in rendered


def test_run_query_success(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite"
    _create_sample_db(db_path)
    schema = load_sqlite_schema(db_path, "test")

    sql, success, display = run_query(
        question="What are the names of all singers from France?",
        schema=schema,
        db_path=db_path,
        model_name="template",
    )
    assert success is True
    assert "WHERE Country = 'France'" in sql
    assert "Alice Martin" in display
    assert "Chloe Dubois" in display


def test_run_scripted_demo_cases(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite"
    _create_sample_db(db_path)

    exit_code = run_scripted_demo(db_path=db_path, database_id="test", model_name="template")
    assert exit_code == 0
    assert len(SCRIPTED_DEMO_CASES) == 3


def test_cli_main_demo_flag(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite"
    _create_sample_db(db_path)

    test_args = ["text-to-sql-demo", "--database", str(db_path), "--demo", "--model", "template"]
    with patch("sys.argv", test_args):
        exit_code = main()
        assert exit_code == 0


def test_cli_main_single_query(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite"
    _create_sample_db(db_path)

    test_args = [
        "text-to-sql-demo",
        "--database",
        str(db_path),
        "--question",
        "What are the names of all singers?",
    ]
    with patch("sys.argv", test_args):
        exit_code = main()
        assert exit_code == 0


def test_build_parser_train_demo_options() -> None:
    args = build_parser().parse_args(["--train-demo", "--epochs", "3", "--train-databases", "a,b"])
    assert args.train_demo
    assert args.epochs == 3
    assert args.train_databases == "a,b"


def test_split_demo_records_is_deterministic_and_per_database() -> None:
    from dataclasses import replace

    from text_to_sql.data.contracts import (
        DatasetSplit,
        ExampleRecord,
        QueryDifficulty,
        QueryStructure,
    )
    from text_to_sql.lstm.train_demo import split_demo_records

    base = ExampleRecord(
        example_id="x",
        dataset="spider",
        split=DatasetSplit.TRAIN,
        database_id="db1",
        database_path=Path("/dev/null"),
        question="q",
        schema_text="table: t",
        gold_sql="SELECT 1",
        difficulty=QueryDifficulty.EASY,
        query_structure=QueryStructure.SINGLE_TABLE,
    )
    records = tuple(
        replace(base, example_id=f"{db}-{i}", database_id=db)
        for db in ("db1", "db2")
        for i in range(10)
    )
    train, held_out = split_demo_records(records, 0.2, seed=7)
    again = split_demo_records(records, 0.2, seed=7)

    assert (train, held_out) == again
    assert len(held_out) == 4
    assert {r.database_id for r in held_out} == {"db1", "db2"}
    assert not {r.example_id for r in train} & {r.example_id for r in held_out}


def test_load_demo_schema_prefers_spider_metadata(tmp_path: Path) -> None:
    import json

    from text_to_sql.cli import load_demo_schema

    db_dir = tmp_path / "spider_data" / "database" / "shop"
    db_dir.mkdir(parents=True)
    db_path = db_dir / "shop.sqlite"
    _create_sample_db(db_path)
    (tmp_path / "spider_data" / "tables.json").write_text(
        json.dumps(
            [
                {
                    "db_id": "shop",
                    "table_names_original": ["singer"],
                    "column_names_original": [[-1, "*"], [0, "Name"]],
                    "column_types": ["text", "text"],
                    "primary_keys": [],
                    "foreign_keys": [],
                }
            ]
        )
    )

    schema = load_demo_schema(db_path, "demo-database")

    assert schema.database_id == "shop"
    assert [c.data_type for c in schema.tables[0].columns] == ["text"]


def test_judge_verdicts(tmp_path: Path) -> None:
    from text_to_sql.cli import judge

    db_path = tmp_path / "test.sqlite"
    _create_sample_db(db_path)
    gold = "SELECT Name FROM singer WHERE Country = 'France'"

    assert judge("SELECT Name FROM singer WHERE Country = 'France'", db_path, gold)[0] == "CORRECT"
    assert judge("SELECT Name FROM singer WHERE Age > 30", db_path, gold)[0] == "WRONG ANSWER"
    assert judge("SELECT Nope FROM singer", db_path, gold)[0] == "EXECUTION ERROR"
    assert judge("", db_path, gold) == ("NO SQL (refused)", None)
    assert judge("SELECT Name FROM singer", db_path, None)[0] == "RAN (not checked)"


def test_cli_main_demo_both_models(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite"
    _create_sample_db(db_path)

    test_args = ["text-to-sql-demo", "--database", str(db_path), "--demo", "--model", "both"]
    with patch("sys.argv", test_args):
        assert main() == 0
