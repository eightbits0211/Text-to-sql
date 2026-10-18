from text_to_sql.data.schema import (
    ColumnSpec,
    DatabaseSchema,
    ForeignKeySpec,
    TableSpec,
    serialize_schema,
)
from text_to_sql.transformer.serialization import build_t5_input, parse_schema_text


def _schema_text() -> str:
    return serialize_schema(
        DatabaseSchema(
            "shop",
            (
                TableSpec(
                    "customers", (ColumnSpec("id", "INTEGER", True), ColumnSpec("name", "TEXT"))
                ),
                TableSpec(
                    "orders",
                    (ColumnSpec("id", "INTEGER", True), ColumnSpec("customer_id", "INTEGER")),
                ),
            ),
            (ForeignKeySpec("orders", "customer_id", "customers", "id"),),
        )
    )


def test_parse_round_trips_tables_columns_and_fks():
    parsed = parse_schema_text(_schema_text())
    assert parsed.database_id == "shop"
    assert parsed.tables == (("customers", ("id", "name")), ("orders", ("customer_id", "id")))
    assert parsed.foreign_keys == ("orders.customer_id -> customers.id",)


def test_build_t5_input_is_compact_and_deterministic():
    text = build_t5_input("How many orders?", _schema_text())
    assert text == (
        "How many orders? | shop | customers : id , name | orders : customer_id , id"
        " | fk : orders.customer_id -> customers.id"
    )
