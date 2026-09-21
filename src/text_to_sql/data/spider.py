"""Spider JSON and schema metadata loading."""

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .contracts import (
    DatasetSplit,
    DatasetStatistics,
    ExampleRecord,
    ExclusionEvent,
    ExclusionReason,
    LoadResult,
    QueryDifficulty,
    QueryStructure,
    SplitStatistics,
)
from .schema import (
    ColumnSpec,
    DatabaseSchema,
    ForeignKeySpec,
    TableSpec,
    serialize_schema,
)
from .sqlite_schema import load_sqlite_schema


def load_spider(
    source_path: Path,
    schema_path: Path,
    database_root: Path,
    *,
    split: DatasetSplit,
    database_pattern: str = "{database_id}/{database_id}.sqlite",
    smoke_limit: int | None = None,
) -> LoadResult:
    """Load an official Spider split and retain records with readable databases."""
    source_records = _read_json_array(source_path)
    schema_records = _read_json_array(schema_path)
    schemas = {
        record.get("db_id"): record
        for record in schema_records
        if isinstance(record.get("db_id"), str)
    }
    if smoke_limit is not None:
        if smoke_limit < 0:
            raise ValueError("smoke_limit must be non-negative")
        source_records = source_records[:smoke_limit]

    retained: list[ExampleRecord] = []
    exclusions: list[ExclusionEvent] = []
    for source_index, source_record in enumerate(source_records):
        example_id = f"spider-{split.value}-{source_index}"
        try:
            retained.append(
                _build_record(
                    source_record,
                    schemas=schemas,
                    source_index=source_index,
                    example_id=example_id,
                    split=split,
                    database_root=database_root,
                    database_pattern=database_pattern,
                )
            )
        except _Excluded as excluded:
            exclusions.append(
                ExclusionEvent(
                    dataset="spider",
                    split=split,
                    source_index=source_index,
                    example_id=example_id,
                    reason=excluded.reason,
                    detail=excluded.detail,
                )
            )

    return LoadResult(
        records=tuple(retained),
        exclusions=tuple(exclusions),
        statistics=_build_statistics(len(source_records), retained, exclusions, split),
    )


def _build_record(
    source_record: dict[str, Any],
    *,
    schemas: dict[str, dict[str, Any]],
    source_index: int,
    example_id: str,
    split: DatasetSplit,
    database_root: Path,
    database_pattern: str,
) -> ExampleRecord:
    question = _text(source_record.get("question"))
    if not question:
        raise _Excluded(ExclusionReason.MISSING_QUESTION, "question is blank")
    gold_sql = _text(source_record.get("query"))
    if not gold_sql:
        raise _Excluded(ExclusionReason.MISSING_GOLD_SQL, "query is blank")
    database_id = _text(source_record.get("db_id"))
    if not database_id:
        raise _Excluded(ExclusionReason.MISSING_DATABASE_ID, "db_id is blank")
    schema_record = schemas.get(database_id)
    if schema_record is None:
        raise _Excluded(ExclusionReason.SCHEMA_UNREADABLE, "schema metadata is missing")
    database_path = database_root / database_pattern.format(database_id=database_id)
    if not database_path.is_file():
        raise _Excluded(ExclusionReason.DATABASE_NOT_FOUND, "database file is missing")
    try:
        schema = _schema_from_metadata(schema_record, database_id)
        sqlite_schema = load_sqlite_schema(database_path, database_id)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise _Excluded(ExclusionReason.SCHEMA_UNREADABLE, str(error)) from error
    difficulty = QueryDifficulty(
        {
            "easy": "easy",
            "medium": "medium",
            "hard": "hard",
            "extra": "extra-hard",
        }.get(_text(source_record.get("hardness")), "unknown")
    )
    return ExampleRecord(
        example_id=example_id,
        dataset="spider",
        split=split,
        database_id=database_id,
        database_path=database_path,
        question=question,
        schema_text=serialize_schema(schema if schema.tables else sqlite_schema),
        gold_sql=gold_sql,
        difficulty=difficulty,
        query_structure=_query_structure(gold_sql),
        source_index=source_index,
    )


def _schema_from_metadata(record: dict[str, Any], database_id: str) -> DatabaseSchema:
    table_names = record["table_names_original"]
    columns_by_table: dict[int, list[ColumnSpec]] = {index: [] for index in range(len(table_names))}
    primary_keys = set(record.get("primary_keys", []))
    for column_index, (table_index, column_name) in enumerate(record["column_names_original"]):
        if table_index < 0:
            continue
        columns_by_table[table_index].append(
            ColumnSpec(
                name=column_name,
                data_type=record["column_types"][column_index],
                is_primary_key=column_index in primary_keys,
            )
        )
    tables = tuple(
        TableSpec(name=table_name, columns=tuple(columns_by_table[index]))
        for index, table_name in enumerate(table_names)
    )
    foreign_keys = tuple(
        ForeignKeySpec(
            source_table=table_names[record["column_names_original"][source][0]],
            source_column=record["column_names_original"][source][1],
            target_table=table_names[record["column_names_original"][target][0]],
            target_column=record["column_names_original"][target][1],
        )
        for source, target in record.get("foreign_keys", [])
    )
    return DatabaseSchema(database_id, tables, foreign_keys)


def _query_structure(query: str) -> QueryStructure:
    normalized = query.lower()
    if any(token in normalized for token in (" join ", " union ", " intersect ", " except ")):
        return QueryStructure.MULTI_TABLE_JOIN
    if re.search(r"\bselect\b.*\bselect\b", normalized, flags=re.DOTALL):
        return QueryStructure.OTHER
    return QueryStructure.SINGLE_TABLE


def _build_statistics(
    source_count: int,
    records: list[ExampleRecord],
    exclusions: list[ExclusionEvent],
    split: DatasetSplit,
) -> DatasetStatistics:
    difficulty_counts = Counter(record.difficulty.value for record in records)
    structure_counts = Counter(record.query_structure.value for record in records)
    return DatasetStatistics(
        dataset="spider",
        total_source_examples=source_count,
        retained_examples=len(records),
        excluded_examples=len(exclusions),
        exclusions_by_reason=dict(
            sorted(Counter(event.reason.value for event in exclusions).items())
        ),
        splits=(
            SplitStatistics(
                split=split,
                example_count=len(records),
                difficulty_counts=dict(sorted(difficulty_counts.items())),
                query_structure_counts=dict(sorted(structure_counts.items())),
                database_count=len({record.database_id for record in records}),
            ),
        ),
        seed=None,
        split_policy="official split supplied by caller",
    )


def _read_json_array(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Spider source does not exist: {path}")
    with path.open(encoding="utf-8") as source_file:
        payload = json.load(source_file)
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError("Spider source must contain a JSON array of objects")
    return payload


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


class _Excluded(Exception):
    def __init__(self, reason: ExclusionReason, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail
