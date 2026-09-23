"""Unit tests for LSTM SQL post-processing and syntax repair."""

from text_to_sql.lstm.sql_repair import parse_schema_identifiers, repair_sql

SCHEMA_SAMPLE = """
database: concert_singer
table: concert
columns:
  - Stadium_ID [text]
  - Year [text]
  - concert_ID [number] [PRIMARY KEY]
table: singer
columns:
  - Age [number]
  - Country [text]
  - Name [text]
  - Singer_ID [number] [PRIMARY KEY]
table: stadium
columns:
  - Capacity [number]
  - Location [text]
  - Name [text]
"""

WIKISQL_SCHEMA_SAMPLE = """
database: 1-10015132-11
table: table_1_10015132_11
columns:
  - Player [text]
  - No. [text]
  - Nationality [text]
  - Position [text]
  - Years in Toronto [text]
  - School/Club Team [text]
"""


def test_parse_schema_identifiers():
    tables, cols, tdict = parse_schema_identifiers(SCHEMA_SAMPLE)
    assert "singer" in tables
    assert "concert" in tables
    assert "stadium" in tables
    assert cols["age"] == "Age"
    assert cols["country"] == "Country"
    assert len(tdict["singer"]) == 4


def test_repair_quotes_string_literal():
    raw_sql = "SELECT AVG ( age ) , MIN ( age ) , MAX ( age ) FROM singer WHERE country = france"
    repaired = repair_sql(raw_sql, SCHEMA_SAMPLE)
    assert "WHERE country = 'france'" in repaired


def test_repair_cleans_spacing_and_aliases():
    raw_sql = "SELECT t1 . Name , COUNT ( * ) FROM stadium AS t1"
    repaired = repair_sql(raw_sql, SCHEMA_SAMPLE)
    assert "t1.Name" in repaired
    assert "COUNT(*)" in repaired


def test_repair_wikisql_multiword_identifiers_and_single_table():
    raw_sql = "SELECT t1 . School/Club Team FROM table_1_10015132_11 AS t1 JOIN stop AS t2 WHERE t1 . Position = guard"
    repaired = repair_sql(raw_sql, WIKISQL_SCHEMA_SAMPLE)
    assert 'FROM "table_1_10015132_11"' in repaired
    assert '"School/Club Team"' in repaired
    assert "WHERE Position = 'guard'" in repaired
    assert "stop" not in repaired


def test_repair_table_hallucination_correction():
    # Model hallucinated 'unknown_table' when all columns belong to 'singer'
    raw_sql = "SELECT Name , Age FROM unknown_table WHERE Age > 20"
    repaired = repair_sql(raw_sql, SCHEMA_SAMPLE)
    assert "FROM singer" in repaired


def test_repair_balances_parentheses():
    raw_sql = "SELECT name FROM stadium WHERE capacity > ( SELECT AVG ( capacity ) FROM stadium"
    repaired = repair_sql(raw_sql, SCHEMA_SAMPLE)
    assert repaired.count("(") == repaired.count(")")
