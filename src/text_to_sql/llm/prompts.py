"""Prompt construction for LLM text-to-SQL (DAIL-SQL style).

The schema is shown as SQLite ``CREATE TABLE`` statements with primary and
foreign keys (the "code representation" that Gao et al. 2023 found strongest),
optionally followed by a few sample rows per table. Few-shot examples are
chosen from Spider train by question similarity, never from the target
database.
"""

from __future__ import annotations

import math
import re
import sqlite3
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from ..data.contracts import ExampleRecord
from ..data.sqlite_schema import load_sqlite_schema

SYSTEM_PROMPT = (
    "You are an expert SQLite developer. Given a database schema and a question, "
    "write one SQLite query that answers it. Use only tables and columns that exist "
    "in the schema. Reply with the SQL only, inside a ```sql code block."
)

_WORD = re.compile(r"[a-z0-9]+")


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def create_table_schema(database_path: Path, database_id: str, sample_rows: int = 0) -> str:
    """Render the database as CREATE TABLE statements (plus optional sample rows)."""
    schema = load_sqlite_schema(database_path, database_id)
    foreign_keys: dict[str, list[str]] = {}
    for fk in schema.foreign_keys:
        foreign_keys.setdefault(fk.source_table, []).append(
            f"  FOREIGN KEY ({_quote(fk.source_column)}) REFERENCES "
            f"{_quote(fk.target_table)}({_quote(fk.target_column)})"
        )
    blocks = []
    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True) if sample_rows else None
    try:
        for table in schema.tables:
            lines = [f"  {_quote(c.name)} {c.data_type}" for c in table.columns]
            keys = [_quote(c.name) for c in table.columns if c.is_primary_key]
            if keys:
                lines.append(f"  PRIMARY KEY ({', '.join(keys)})")
            lines.extend(foreign_keys.get(table.name, []))
            block = f"CREATE TABLE {_quote(table.name)} (\n" + ",\n".join(lines) + "\n);"
            if connection is not None:
                rows = connection.execute(
                    f"SELECT * FROM {_quote(table.name)} LIMIT {int(sample_rows)}"
                ).fetchall()
                if rows:
                    header = " | ".join(c.name for c in table.columns)
                    body = "\n".join(" | ".join(str(v) for v in row) for row in rows)
                    block += f"\n/* {len(rows)} example rows:\n{header}\n{body}\n*/"
            blocks.append(block)
    finally:
        if connection is not None:
            connection.close()
    return "\n\n".join(blocks)


def _bag(text: str) -> Counter[str]:
    return Counter(_WORD.findall(text.lower()))


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    dot = sum(a[t] * b[t] for t in a.keys() & b.keys())
    norm = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return dot / norm if norm else 0.0


@dataclass
class FewShotSelector:
    """Pick the k most similar training questions from other databases."""

    pool: Sequence[ExampleRecord]

    def __post_init__(self) -> None:
        self._bags = [_bag(ex.question) for ex in self.pool]

    def select(self, example: ExampleRecord, k: int) -> list[ExampleRecord]:
        if k <= 0:
            return []
        target = _bag(example.question)
        scored = [
            (_cosine(target, bag), index)
            for index, bag in enumerate(self._bags)
            if self.pool[index].database_id != example.database_id
        ]
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [self.pool[index] for _, index in scored[:k]]


def build_messages(
    example: ExampleRecord,
    shots: Sequence[ExampleRecord] = (),
    sample_rows: int = 3,
) -> list[dict[str, str]]:
    """Chat messages: system, then (question, SQL) shot pairs, then the target question."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for shot in shots:
        messages.append(
            {
                "role": "user",
                "content": _user_turn(
                    shot, create_table_schema(shot.database_path, shot.database_id)
                ),
            }
        )
        messages.append({"role": "assistant", "content": f"```sql\n{shot.gold_sql}\n```"})
    schema = create_table_schema(example.database_path, example.database_id, sample_rows)
    messages.append({"role": "user", "content": _user_turn(example, schema)})
    return messages


def _user_turn(example: ExampleRecord, schema: str) -> str:
    return f"Database schema:\n{schema}\n\nQuestion: {example.question}"


_SQL_BLOCK = re.compile(r"```(?:sql|sqlite)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_SELECT = re.compile(r"\b(SELECT|WITH)\b.*", re.DOTALL | re.IGNORECASE)


def extract_sql(response: str) -> str:
    """Take the last ```sql block, else the text from the first SELECT/WITH; one line, no ';'."""
    blocks = _SQL_BLOCK.findall(response)
    text = blocks[-1] if blocks else (m.group(0) if (m := _SELECT.search(response)) else "")
    text = " ".join(text.split())
    return text.split(";")[0].strip()
