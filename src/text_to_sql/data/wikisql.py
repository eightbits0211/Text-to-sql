"""WikiSQL JSON loading with configurable SQLite database resolution."""

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
from .schema import ColumnSpec, DatabaseSchema, TableSpec, serialize_schema
from .sqlite_schema import load_sqlite_schema


def load_wikisql(
    source_path: Path,
    database_root: Path,
    *,
    split: DatasetSplit,
    database_pattern: str = "{database_id}.db",
    table_metadata_path: Path | None = None,
    smoke_limit: int | None = None,
) -> LoadResult:
    """Load standard WikiSQL records and retain single-table queries.

    The source must be a JSON array. Each record must contain ``question``,
    ``table.id``, ``table.header``, and either a complete ``sql.query`` string
    or structured ``sql`` fields (``sel``, ``agg``, and ``conds``).
    """
    source_records = _read_records(source_path)
    table_metadata = _read_table_metadata(table_metadata_path) if table_metadata_path else {}
    if smoke_limit is not None:
        if smoke_limit < 0:
            raise ValueError("smoke_limit must be non-negative")
        source_records = source_records[:smoke_limit]

    retained: list[ExampleRecord] = []
    exclusions: list[ExclusionEvent] = []
    verified_databases: set[Path] = set()
    for source_index, source_record in enumerate(source_records):
        example_id = f"wikisql-{split.value}-{source_index}"
        try:
            record = _build_record(
                source_record,
                source_index=source_index,
                example_id=example_id,
                split=split,
                database_root=database_root,
                database_pattern=database_pattern,
                table_metadata=table_metadata,
                verified_databases=verified_databases,
            )
        except _Excluded as excluded:
            exclusions.append(
                ExclusionEvent(
                    dataset="wikisql",
                    split=split,
                    source_index=source_index,
                    example_id=example_id,
                    reason=excluded.reason,
                    detail=excluded.detail,
                )
            )
        else:
            retained.append(record)

    return LoadResult(
        records=tuple(retained),
        exclusions=tuple(exclusions),
        statistics=_build_statistics(len(source_records), retained, exclusions, split),
    )


def _read_records(source_path: Path) -> list[dict[str, Any]]:
    if not source_path.is_file():
        raise FileNotFoundError(f"WikiSQL source does not exist: {source_path}")
    with source_path.open(encoding="utf-8") as source_file:
        if source_path.suffix == ".jsonl":
            payload = [json.loads(line) for line in source_file if line.strip()]
        else:
            payload = json.load(source_file)
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError("WikiSQL source must contain a JSON array of objects")
    return payload


def _read_table_metadata(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"WikiSQL table metadata does not exist: {path}")
    with path.open(encoding="utf-8") as source_file:
        records = [json.loads(line) for line in source_file if line.strip()]
    return {
        record["id"]: record
        for record in records
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }


def _build_record(
    source_record: dict[str, Any],
    *,
    source_index: int,
    example_id: str,
    split: DatasetSplit,
    database_root: Path,
    database_pattern: str,
    table_metadata: dict[str, dict[str, Any]],
    verified_databases: set[Path] | None = None,
) -> ExampleRecord:
    question = _text(source_record.get("question"))
    if not question:
        raise _Excluded(ExclusionReason.MISSING_QUESTION, "question is blank")

    embedded_table = source_record.get("table")
    table = embedded_table
    if table is None and isinstance(source_record.get("table_id"), str):
        table = table_metadata.get(source_record["table_id"])
    if not isinstance(table, dict):
        raise _Excluded(ExclusionReason.MALFORMED_SOURCE_RECORD, "table object is missing")
    database_id = _text(table.get("id") or source_record.get("table_id"))
    if not database_id:
        raise _Excluded(ExclusionReason.MISSING_DATABASE_ID, "table.id is blank")
    headers = table.get("header")
    if not isinstance(headers, list) or not headers:
        raise _Excluded(ExclusionReason.SCHEMA_UNREADABLE, "table.header is missing")

    table_name = (
        _text(table.get("name")) or database_id
        if embedded_table is not None
        else f"table_{database_id.replace('-', '_')}"
    )
    gold_sql = _build_sql(source_record.get("sql"), headers, table_name)
    if not gold_sql:
        raise _Excluded(ExclusionReason.MISSING_GOLD_SQL, "SQL is missing or blank")
    if not _is_single_table_query(gold_sql, table_name):
        raise _Excluded(
            ExclusionReason.UNSUPPORTED_QUERY_STRUCTURE,
            "query references more than one table or a nested query",
        )

    database_path = database_root / database_pattern.format(database_id=database_id)
    if not database_path.is_file():
        raise _Excluded(
            ExclusionReason.DATABASE_NOT_FOUND,
            f"database file not found for {database_id}",
        )
    if verified_databases is None or database_path not in verified_databases:
        try:
            load_sqlite_schema(database_path, database_id)
            if verified_databases is not None:
                verified_databases.add(database_path)
        except (OSError, ValueError) as error:
            raise _Excluded(ExclusionReason.DATABASE_UNREADABLE, str(error)) from error

    schema = DatabaseSchema(
        database_id,
        (
            TableSpec(
                table_name,
                tuple(
                    ColumnSpec(str(header), str(data_type))
                    for header, data_type in zip(
                        headers,
                        table.get("types", ["TEXT"] * len(headers)),
                        strict=True,
                    )
                ),
            ),
        ),
    )

    return ExampleRecord(
        example_id=example_id,
        dataset="wikisql",
        split=split,
        database_id=database_id,
        database_path=database_path,
        question=question,
        schema_text=serialize_schema(schema),
        gold_sql=gold_sql,
        difficulty=QueryDifficulty.UNKNOWN,
        query_structure=QueryStructure.SINGLE_TABLE,
        source_index=source_index,
    )


def _build_sql(sql_payload: Any, headers: list[Any], table_name: str) -> str:
    if isinstance(sql_payload, dict):
        complete_query = _text(sql_payload.get("query"))
        if complete_query:
            return complete_query
        selected = sql_payload.get("sel")
        aggregation = sql_payload.get("agg", 0)
        conditions = sql_payload.get("conds", [])
        if not isinstance(selected, int) or not 0 <= selected < len(headers):
            return ""
        if not isinstance(conditions, list):
            return ""
        column = _quote_identifier(str(headers[selected]))
        expression = f"SELECT {column}"
        aggregation_name = _aggregation_name(aggregation)
        if aggregation_name:
            expression = f"SELECT {aggregation_name}({column})"
        expression += f" FROM {_quote_identifier(table_name)}"
        where_clauses = []
        for condition in conditions:
            if not isinstance(condition, list) or len(condition) != 3:
                return ""
            condition_column, operator, value = condition
            if not isinstance(condition_column, int) or not 0 <= condition_column < len(headers):
                return ""
            where_clauses.append(
                f"{_quote_identifier(str(headers[condition_column]))} "
                f"{_operator(str(operator))} {_quote_literal(value)}"
            )
        if where_clauses:
            expression += " WHERE " + " AND ".join(where_clauses)
        return expression
    return _text(sql_payload)


def _aggregation_name(aggregation: Any) -> str:
    return {
        0: "",
        1: "MAX",
        2: "MIN",
        3: "COUNT",
        4: "SUM",
        5: "AVG",
    }.get(aggregation, "")


def _operator(operator: str) -> str:
    return {"=": "=", "!=": "!=", "<": "<", ">": ">", "<=": "<=", ">=": ">="}.get(
        operator,
        "=",
    )


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _quote_literal(value: Any) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _is_single_table_query(query: str, table_name: str) -> bool:
    normalized = query.lower()
    if any(keyword in normalized for keyword in (" join ", " union ", " intersect ", " except ")):
        return False
    if re.search(r"\bselect\b.*\bselect\b", normalized, flags=re.DOTALL):
        return False
    from_match = re.search(r"\bfrom\s+([`\"A-Za-z_][\w`\"]*)", query, flags=re.IGNORECASE)
    return bool(from_match and from_match.group(1).strip('`"').lower() == table_name.lower())


def _build_statistics(
    source_count: int,
    records: list[ExampleRecord],
    exclusions: list[ExclusionEvent],
    split: DatasetSplit,
) -> DatasetStatistics:
    difficulty_counts = Counter(record.difficulty.value for record in records)
    structure_counts = Counter(record.query_structure.value for record in records)
    split_statistics = SplitStatistics(
        split=split,
        example_count=len(records),
        difficulty_counts=dict(sorted(difficulty_counts.items())),
        query_structure_counts=dict(sorted(structure_counts.items())),
        database_count=len({record.database_id for record in records}),
    )
    return DatasetStatistics(
        dataset="wikisql",
        total_source_examples=source_count,
        retained_examples=len(records),
        excluded_examples=len(exclusions),
        exclusions_by_reason=dict(
            sorted(Counter(event.reason.value for event in exclusions).items())
        ),
        splits=(split_statistics,),
        seed=None,
        split_policy="source split supplied by caller",
    )


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


class _Excluded(Exception):
    def __init__(self, reason: ExclusionReason, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail
