"""Compact T5 input serialization (Shaw et al. 2021 / PICARD style).

``question | db_id | table : col1 , col2 | table2 : ...`` with optional
foreign keys, built from the verbose ``serialize_schema`` text that every
``ExampleRecord`` already carries. Lowercased identifiers are kept verbatim so
the constrained decoder can match them against the database schema.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedSchema:
    database_id: str
    tables: tuple[tuple[str, tuple[str, ...]], ...]
    foreign_keys: tuple[str, ...]


def parse_schema_text(schema_text: str) -> ParsedSchema:
    """Invert ``data.schema.serialize_schema`` into tables, columns and FKs."""
    database_id = ""
    tables: list[tuple[str, list[str]]] = []
    foreign_keys: list[str] = []
    section = ""
    for raw_line in schema_text.splitlines():
        line = raw_line.strip()
        if line.startswith("database:"):
            database_id = line.split(":", 1)[1].strip()
        elif line.startswith("table:"):
            tables.append((line.split(":", 1)[1].strip(), []))
            section = "table"
        elif line == "columns:":
            section = "columns"
        elif line == "foreign_keys:":
            section = "fks"
        elif line.startswith("- "):
            item = line[2:]
            if section == "columns" and tables:
                tables[-1][1].append(item.split(" [", 1)[0].strip())
            elif section == "fks":
                foreign_keys.append(item.strip())
    if not tables:
        raise ValueError("schema text contains no tables")
    return ParsedSchema(
        database_id=database_id,
        tables=tuple((name, tuple(columns)) for name, columns in tables),
        foreign_keys=tuple(foreign_keys),
    )


def build_t5_input(question: str, schema_text: str, include_foreign_keys: bool = True) -> str:
    parsed = parse_schema_text(schema_text)
    parts = [question.strip(), parsed.database_id]
    for table, columns in parsed.tables:
        parts.append(f"{table} : {' , '.join(columns)}")
    if include_foreign_keys and parsed.foreign_keys:
        parts.append("fk : " + " , ".join(parsed.foreign_keys))
    return " | ".join(parts)
