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
    difficulty = _classify_difficulty(source_record.get("sql"))
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


# ---------------------------------------------------------------------------
# Official Spider difficulty classification
# ---------------------------------------------------------------------------
# Reimplements the eval_hardness logic from the official Spider evaluation
# script (https://github.com/taoyds/spider/blob/master/evaluation.py).
# Uses the parsed ``sql`` dict shipped in the Spider JSON files.
# ---------------------------------------------------------------------------

_COMP1_KEYWORDS = frozenset({"where", "group", "order", "limit", "join", "or", "like"})
_COMP2_KEYWORDS = frozenset({"except", "union", "intersect"})
_WHERE_OPS = (
    "not",
    "between",
    "=",
    ">",
    "<",
    ">=",
    "<=",
    "!=",
    "in",
    "like",
    "is",
    "exists",
)


def _has_agg(unit: list) -> bool:
    """Return True if a select/val unit uses an aggregate (index != 0 = 'none')."""
    return bool(unit and unit[0] != 0)


def _count_agg(units: list) -> int:
    return sum(1 for unit in units if _has_agg(unit))


def _count_component1(sql_dict: dict[str, Any]) -> int:
    """Count component-1 features: where, group, order, limit, join, or, like."""
    count = 0
    if len(sql_dict.get("where", [])) > 0:
        count += 1
    if len(sql_dict.get("groupBy", [])) > 0:
        count += 1
    if len(sql_dict.get("orderBy", [])) > 0:
        count += 1
    if sql_dict.get("limit") is not None:
        count += 1
    table_units = sql_dict.get("from", {}).get("table_units", [])
    if len(table_units) > 0:
        count += len(table_units) - 1

    from_conds = sql_dict.get("from", {}).get("conds", [])
    where_conds = sql_dict.get("where", [])
    having_conds = sql_dict.get("having", [])
    all_and_ors = from_conds[1::2] + where_conds[1::2] + having_conds[1::2]
    count += sum(1 for token in all_and_ors if token == "or")

    like_idx = _WHERE_OPS.index("like")
    cond_units = from_conds[::2] + where_conds[::2] + having_conds[::2]
    count += sum(1 for cu in cond_units if len(cu) > 1 and cu[1] == like_idx)
    return count


def _get_nested_sql(sql_dict: dict[str, Any]) -> list[dict[str, Any]]:
    nested: list[dict[str, Any]] = []
    from_conds = sql_dict.get("from", {}).get("conds", [])
    where_conds = sql_dict.get("where", [])
    having_conds = sql_dict.get("having", [])
    for cond_unit in from_conds[::2] + where_conds[::2] + having_conds[::2]:
        if len(cond_unit) > 3 and isinstance(cond_unit[3], dict):
            nested.append(cond_unit[3])
        if len(cond_unit) > 4 and isinstance(cond_unit[4], dict):
            nested.append(cond_unit[4])
    for key in ("intersect", "except", "union"):
        val = sql_dict.get(key)
        if val is not None:
            nested.append(val)
    return nested


def _count_component2(sql_dict: dict[str, Any]) -> int:
    """Count component-2 features: nested subqueries and set ops."""
    return len(_get_nested_sql(sql_dict))


def _count_others(sql_dict: dict[str, Any]) -> int:
    """Count 'other' complexity indicators: aggregations, select columns,
    multiple where conditions, multiple group by clauses."""
    count = 0
    select_items = sql_dict.get("select", [False, []])[1]
    where_units = sql_dict.get("where", [])[::2]
    group_units = sql_dict.get("groupBy", [])
    order_items = sql_dict.get("orderBy", [])
    order_units: list = []
    if len(order_items) > 1 and isinstance(order_items[1], list):
        for unit in order_items[1]:
            if len(unit) > 1 and unit[1]:
                order_units.append(unit[1])
            if len(unit) > 2 and unit[2]:
                order_units.append(unit[2])
    having_units = sql_dict.get("having", [])

    agg_count = _count_agg(select_items)
    agg_count += _count_agg(where_units)
    agg_count += _count_agg(group_units)
    agg_count += _count_agg(order_units)
    agg_count += _count_agg(having_units)
    if agg_count > 1:
        count += 1

    if len(select_items) > 1:
        count += 1
    if len(sql_dict.get("where", [])) > 1:
        count += 1
    if len(sql_dict.get("groupBy", [])) > 1:
        count += 1
    return count


def _classify_difficulty(sql_dict: dict | None) -> QueryDifficulty:
    """Classify a Spider example's difficulty from its parsed SQL dict.

    Reimplements the official Spider ``eval_hardness`` logic.
    Falls back to UNKNOWN if no parsed SQL dict is available.
    """
    if not sql_dict or not isinstance(sql_dict, dict):
        return QueryDifficulty.UNKNOWN

    try:
        comp1 = _count_component1(sql_dict)
        comp2 = _count_component2(sql_dict)
        others = _count_others(sql_dict)
    except (KeyError, TypeError, IndexError):
        return QueryDifficulty.UNKNOWN

    if comp1 <= 1 and others == 0 and comp2 == 0:
        return QueryDifficulty.EASY
    if (others <= 2 and comp1 <= 1 and comp2 == 0) or (comp1 <= 2 and others < 2 and comp2 == 0):
        return QueryDifficulty.MEDIUM
    if (
        (others > 2 and comp1 <= 2 and comp2 == 0)
        or (2 < comp1 <= 3 and others <= 2 and comp2 == 0)
        or (comp1 <= 1 and others == 0 and comp2 <= 1)
    ):
        return QueryDifficulty.HARD
    return QueryDifficulty.EXTRA_HARD


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
