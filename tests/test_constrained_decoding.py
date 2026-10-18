import sqlite3

import torch

from text_to_sql.transformer.constrained import (
    SchemaConstraintProcessor,
    allowed_words,
    explain_valid,
    first_valid,
    invalid_word,
)

SCHEMA = (
    "database: shop\ntable: customers\ncolumns:\n  - id [INTEGER]\n  - name [TEXT]\n"
    "table: orders\ncolumns:\n  - customer_id [INTEGER]\n  - id [INTEGER]\nforeign_keys:"
)
ALLOWED = allowed_words(SCHEMA, "How many orders did Ada place?")


def test_valid_queries_pass():
    for sql in (
        "SELECT count(*) FROM orders",
        "SELECT T1.name FROM customers AS T1 JOIN orders AS T2 ON T1.id = T2.customer_id",
        "SELECT name FROM customers WHERE name = 'Zed Unknown'",
        "SELECT name FROM customers WHERE name = Ada",
        "SELECT count(*) AS total FROM orders ORDER BY total DESC LIMIT 1",
    ):
        assert invalid_word(sql + " ", ALLOWED) is None, sql


def test_unknown_identifier_is_caught_once_complete():
    assert invalid_word("SELECT price FROM orders", ALLOWED) == "price"
    # still being typed: the trailing word may grow into a valid identifier
    assert invalid_word("SELECT cust", ALLOWED) is None
    assert invalid_word("SELECT cust ", ALLOWED) == "cust"


def test_processor_prunes_only_bad_beams():
    class Tok:
        def batch_decode(self, ids, skip_special_tokens=True):
            return ["SELECT name FROM ", "SELECT price FROM "]

    processor = SchemaConstraintProcessor(Tok(), SCHEMA, "q")
    scores = torch.zeros(2, 5)
    out = processor(torch.zeros(2, 3, dtype=torch.long), scores)
    assert torch.isfinite(out[0]).all()
    assert torch.isinf(out[1]).all()
    assert processor.pruned == 1


def test_explain_and_first_valid(tmp_path):
    db = tmp_path / "shop.sqlite"
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE customers (id INTEGER, name TEXT)")
    assert explain_valid("SELECT name FROM customers", db)
    assert not explain_valid("SELECT price FROM customers", db)
    assert not explain_valid("SELEC name", db)
    assert not explain_valid("", db)
    assert first_valid(["SELECT price FROM customers", "SELECT id FROM customers"], db) == (
        "SELECT id FROM customers"
    )
    assert first_valid(["bad sql"], db) == "bad sql"
