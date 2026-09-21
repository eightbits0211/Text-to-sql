"""Typed contracts shared by dataset loaders and downstream components."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class DatasetSplit(StrEnum):
    TRAIN = "train"
    DEV = "dev"
    TEST = "test"


class QueryDifficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXTRA_HARD = "extra-hard"
    UNKNOWN = "unknown"


class QueryStructure(StrEnum):
    SINGLE_TABLE = "single_table"
    MULTI_TABLE_JOIN = "multi_table_join"
    OTHER = "other"


class ExclusionReason(StrEnum):
    MISSING_QUESTION = "missing_question"
    MISSING_GOLD_SQL = "missing_gold_sql"
    MISSING_DATABASE_ID = "missing_database_id"
    DATABASE_NOT_FOUND = "database_not_found"
    DATABASE_UNREADABLE = "database_unreadable"
    SCHEMA_UNREADABLE = "schema_unreadable"
    UNSUPPORTED_QUERY_STRUCTURE = "unsupported_query_structure"
    MALFORMED_SOURCE_RECORD = "malformed_source_record"


@dataclass(frozen=True)
class ExampleRecord:
    example_id: str
    dataset: str
    split: DatasetSplit
    database_id: str
    database_path: Path
    question: str
    schema_text: str
    gold_sql: str
    difficulty: QueryDifficulty
    query_structure: QueryStructure
    source_index: int | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "example_id",
            "dataset",
            "database_id",
            "question",
            "schema_text",
            "gold_sql",
        ):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be empty")


@dataclass(frozen=True)
class ExclusionEvent:
    dataset: str
    split: DatasetSplit | None
    source_index: int | None
    example_id: str | None
    reason: ExclusionReason
    detail: str


@dataclass(frozen=True)
class SplitStatistics:
    split: DatasetSplit
    example_count: int
    difficulty_counts: dict[str, int]
    query_structure_counts: dict[str, int]
    database_count: int


@dataclass(frozen=True)
class DatasetStatistics:
    dataset: str
    total_source_examples: int
    retained_examples: int
    excluded_examples: int
    exclusions_by_reason: dict[str, int]
    splits: tuple[SplitStatistics, ...]
    seed: int | None
    split_policy: str


@dataclass(frozen=True)
class LoadResult:
    records: tuple[ExampleRecord, ...]
    exclusions: tuple[ExclusionEvent, ...]
    statistics: DatasetStatistics
