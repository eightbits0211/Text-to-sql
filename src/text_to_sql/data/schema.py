"""Deterministic database schema serialization."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    data_type: str
    is_primary_key: bool = False


@dataclass(frozen=True)
class ForeignKeySpec:
    source_table: str
    source_column: str
    target_table: str
    target_column: str


@dataclass(frozen=True)
class TableSpec:
    name: str
    columns: tuple[ColumnSpec, ...]


@dataclass(frozen=True)
class DatabaseSchema:
    database_id: str
    tables: tuple[TableSpec, ...]
    foreign_keys: tuple[ForeignKeySpec, ...] = ()


def serialize_schema(schema: DatabaseSchema) -> str:
    """Serialize a schema into a stable, model-ready text representation."""
    if not schema.database_id.strip():
        raise ValueError("database_id must not be empty")
    if not schema.tables:
        raise ValueError("schema must contain at least one table")

    lines = [f"database: {schema.database_id}"]
    for table in sorted(schema.tables, key=lambda item: item.name):
        if not table.name.strip():
            raise ValueError("table names must not be empty")
        lines.append(f"table: {table.name}")
        lines.append("columns:")
        for column in sorted(table.columns, key=lambda item: item.name):
            if not column.name.strip() or not column.data_type.strip():
                raise ValueError("column names and types must not be empty")
            primary_key = " [PRIMARY KEY]" if column.is_primary_key else ""
            lines.append(f"  - {column.name} [{column.data_type}]{primary_key}")

    lines.append("foreign_keys:")
    for foreign_key in sorted(
        schema.foreign_keys,
        key=lambda item: (
            item.source_table,
            item.source_column,
            item.target_table,
            item.target_column,
        ),
    ):
        lines.append(
            "  - "
            f"{foreign_key.source_table}.{foreign_key.source_column} -> "
            f"{foreign_key.target_table}.{foreign_key.target_column}"
        )
    return "\n".join(lines)
