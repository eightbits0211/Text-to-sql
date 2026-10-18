import sqlite3

import pytest

from text_to_sql.generation.exec_correction import correction_loop, execution_rerank


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "shop.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE customers (id INTEGER, name TEXT)")
        connection.execute("INSERT INTO customers VALUES (1, 'Ada')")
    return path


def test_rerank_skips_errors_and_prefers_rows(db):
    candidates = [
        "SELECT price FROM customers",
        "SELECT name FROM customers WHERE id = 99",
        "SELECT name FROM customers",
    ]
    result = execution_rerank(candidates, db)
    assert result.chosen_index == 2
    assert result.statuses == ("invalid_sql", "empty", "success")
    assert execution_rerank(candidates, db, prefer_nonempty=False).chosen_index == 1


def test_rerank_falls_back_to_first_empty_then_top_beam(db):
    empty = execution_rerank(
        ["SELECT price FROM customers", "SELECT id FROM customers WHERE 0"], db
    )
    assert empty.chosen_index == 1
    none = execution_rerank(["bad", "also bad"], db)
    assert (none.sql, none.chosen_index) == ("bad", 0)


def test_correction_loop_feeds_error_back_and_stops_on_success(db):
    replies = iter(
        ["```sql\nSELECT price FROM customers\n```", "```sql\nSELECT name FROM customers\n```"]
    )
    seen = []

    def generate(messages):
        seen.append(messages)
        return next(replies)

    def extract(text):
        return text.split("```sql\n")[1].split("\n```")[0]

    result = correction_loop(
        generate, extract, [{"role": "user", "content": "q"}], db, max_retries=2
    )
    assert result.sql == "SELECT name FROM customers"
    assert result.attempts == 2
    assert "no such column: price" in seen[1][-1]["content"]


def test_correction_loop_respects_retry_budget(db):
    calls = []

    def generate(messages):
        calls.append(1)
        return "SELECT price FROM customers"

    result = correction_loop(generate, lambda text: text, [], db, max_retries=1)
    assert len(calls) == 2
    assert result.final_status == "invalid_sql"
    assert len(result.errors) == 2
