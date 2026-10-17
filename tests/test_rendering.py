"""Tests for surface-form rendering of decoded LSTM tokens."""

from test_sql_repair import SCHEMA_SAMPLE, WIKISQL_SCHEMA_SAMPLE

from text_to_sql.lstm.rendering import blocked_markup_tokens, render_sql
from text_to_sql.lstm.sql_repair import repair_sql


def test_render_restores_literal_case_from_question() -> None:
    sql = render_sql(
        ["SELECT", "avg", "(", "age", ")", "FROM", "singer", "WHERE", "country", "=", "france"],
        "What is the average age of all singers from France?",
        SCHEMA_SAMPLE,
    )
    assert sql.endswith("WHERE Country = 'France'")


def test_render_keeps_multiword_literal_as_one_quoted_value() -> None:
    sql = render_sql(
        ["SELECT", "name", "FROM", "singer", "WHERE", "country", "=", "united states"],
        "Which singers are from the United States?",
        SCHEMA_SAMPLE,
    )
    repaired = repair_sql(sql, SCHEMA_SAMPLE)
    assert "Country = 'United States'" in repaired


def test_render_restores_wikisql_identifier_spelling_and_quotes() -> None:
    sql = render_sql(
        ["SELECT", "player", "FROM", "table_1_10015132_11", "WHERE", "no.", "=", "42"],
        "Who is the player that wears number 42?",
        WIKISQL_SCHEMA_SAMPLE,
    )
    assert sql == 'SELECT Player FROM table_1_10015132_11 WHERE "No." = 42'


def test_render_does_not_quote_column_or_alias_comparisons() -> None:
    sql = render_sql(["t1", ".", "singer_id", "=", "t2", ".", "singer_id"], "q", SCHEMA_SAMPLE)
    assert "'" not in sql


def test_blocked_markup_tokens_excludes_real_columns() -> None:
    blocked = blocked_markup_tokens(SCHEMA_SAMPLE)
    assert "text" in blocked
    assert "number" in blocked
    schema_with_text_column = SCHEMA_SAMPLE + "table: notes\ncolumns:\n  - text [text]\n"
    assert "text" not in blocked_markup_tokens(schema_with_text_column)


def test_repair_does_not_split_quoted_literals() -> None:
    repaired = repair_sql(
        "SELECT Name FROM stadium WHERE Location = 'St. Louis , MO'", SCHEMA_SAMPLE
    )
    assert "'St. Louis , MO'" in repaired
