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
    args = parser.parse_args(["--database", "test.db", "--question", "Show names", "--model", "template"])
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
    assert 'WHERE "Country" = \'France\'' in sql
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
