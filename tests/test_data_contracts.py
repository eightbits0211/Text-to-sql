from pathlib import Path

import pytest

from text_to_sql.data.contracts import (
    DatasetSplit,
    ExampleRecord,
    QueryDifficulty,
    QueryStructure,
)
from text_to_sql.data.schema import (
    ColumnSpec,
    DatabaseSchema,
    ForeignKeySpec,
    TableSpec,
    serialize_schema,
)


def test_example_record_rejects_empty_required_fields(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="question"):
        ExampleRecord(
            example_id="example-1",
            dataset="wikisql",
            split=DatasetSplit.TRAIN,
            database_id="fixture",
            database_path=tmp_path / "fixture.db",
            question=" ",
            schema_text="table: people",
            gold_sql="SELECT 1",
            difficulty=QueryDifficulty.UNKNOWN,
            query_structure=QueryStructure.SINGLE_TABLE,
        )


def test_schema_serialization_is_deterministic() -> None:
    schema = DatabaseSchema(
        database_id="fixture",
        tables=(
            TableSpec("orders", (ColumnSpec("customer_id", "INTEGER"),)),
            TableSpec("customers", (ColumnSpec("id", "INTEGER", True),)),
        ),
        foreign_keys=(ForeignKeySpec("orders", "customer_id", "customers", "id"),),
    )

    assert serialize_schema(schema) == (
        "database: fixture\n"
        "table: customers\n"
        "columns:\n"
        "  - id [INTEGER] [PRIMARY KEY]\n"
        "table: orders\n"
        "columns:\n"
        "  - customer_id [INTEGER]\n"
        "foreign_keys:\n"
        "  - orders.customer_id -> customers.id"
    )
