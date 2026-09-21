import sqlite3
from pathlib import Path

import pytest

from text_to_sql.data.schema import serialize_schema
from text_to_sql.data.sqlite_schema import load_sqlite_schema


def _create_fixture_database(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                note TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );
            """
        )
        connection.commit()
    finally:
        connection.close()


def test_load_sqlite_schema_reads_tables_keys_and_types(tmp_path: Path) -> None:
    database_path = tmp_path / "fixture.sqlite"
    _create_fixture_database(database_path)

    schema = load_sqlite_schema(database_path, "fixture")

    assert [table.name for table in schema.tables] == ["customers", "orders"]
    assert schema.tables[0].columns[0].is_primary_key is True
    assert schema.tables[1].columns[2].data_type == "TEXT"
    assert schema.foreign_keys[0].source_table == "orders"
    assert schema.foreign_keys[0].target_table == "customers"
    assert "orders.customer_id -> customers.id" in serialize_schema(schema)


def test_load_sqlite_schema_does_not_allow_missing_database(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        load_sqlite_schema(tmp_path / "missing.sqlite", "fixture")


def test_load_sqlite_schema_rejects_empty_database(tmp_path: Path) -> None:
    database_path = tmp_path / "empty.sqlite"
    sqlite3.connect(database_path).close()

    with pytest.raises(ValueError, match="no user tables"):
        load_sqlite_schema(database_path, "fixture")
