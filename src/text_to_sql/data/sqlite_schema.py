import functools
import sqlite3
from pathlib import Path

from .schema import ColumnSpec, DatabaseSchema, ForeignKeySpec, TableSpec


@functools.lru_cache(maxsize=1024)
def _introspect_sqlite(
    database_path_str: str,
) -> tuple[tuple[TableSpec, ...], tuple[ForeignKeySpec, ...]]:
    database_path = Path(database_path_str)
    uri = f"file:{database_path.resolve()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as error:
        raise OSError(f"Could not open SQLite database read-only: {database_path}") from error

    try:
        table_names = _load_table_names(connection)
        tables = tuple(
            TableSpec(
                name=table_name,
                columns=_load_columns(connection, table_name),
            )
            for table_name in table_names
        )
        foreign_keys = tuple(
            foreign_key
            for table_name in table_names
            for foreign_key in _load_foreign_keys(connection, table_name)
        )
    except sqlite3.Error as error:
        raise OSError(f"Could not read SQLite schema: {database_path}") from error
    finally:
        connection.close()

    if not tables:
        raise ValueError(f"SQLite database contains no user tables: {database_path}")
    return tables, foreign_keys


def load_sqlite_schema(database_path: Path, database_id: str) -> DatabaseSchema:
    """Load tables, columns, primary keys, and foreign keys from SQLite."""
    if not database_id.strip():
        raise ValueError("database_id must not be empty")
    if not database_path.is_file():
        raise FileNotFoundError(f"SQLite database does not exist: {database_path}")

    tables, foreign_keys = _introspect_sqlite(str(database_path.resolve()))
    return DatabaseSchema(database_id, tables, foreign_keys)


def _load_table_names(connection: sqlite3.Connection) -> tuple[str, ...]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()
    return tuple(row[0] for row in rows)


def _load_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> tuple[ColumnSpec, ...]:
    rows = connection.execute(f'PRAGMA table_info("{_quote_identifier(table_name)}")').fetchall()
    return tuple(
        ColumnSpec(
            name=row[1],
            data_type=row[2] or "UNKNOWN",
            is_primary_key=bool(row[5]),
        )
        for row in rows
    )


def _load_foreign_keys(
    connection: sqlite3.Connection,
    table_name: str,
) -> tuple[ForeignKeySpec, ...]:
    rows = connection.execute(
        f'PRAGMA foreign_key_list("{_quote_identifier(table_name)}")'
    ).fetchall()
    return tuple(
        ForeignKeySpec(
            source_table=table_name,
            source_column=row[3],
            target_table=row[2],
            target_column=row[4],
        )
        for row in rows
    )


def _quote_identifier(identifier: str) -> str:
    return identifier.replace('"', '""')
