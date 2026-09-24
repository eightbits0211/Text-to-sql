"""Schema-aware post-processing and syntax repair for LSTM Text-to-SQL predictions.

Repairs common Seq2Seq autoregressive generation defects:
1. Spacing around dots, parentheses, and aggregates (e.g., 't1 . col' -> 't1.col', 'COUNT ( * )' -> 'COUNT(*)').
2. String literal quoting in WHERE comparison predicates (e.g., 'country = france' -> 'country = \\'france\\'').
3. Multi-word identifier quoting for SQLite compatibility (e.g., 'school/club team' -> '"school/club team"').
4. Hallucinated table name correction to valid schema tables.
5. Incomplete trailing operators and unbalanced parentheses.
"""

from __future__ import annotations

import re

SQL_KEYWORDS = {
    "SELECT",
    "FROM",
    "WHERE",
    "AND",
    "OR",
    "NOT",
    "IN",
    "LIKE",
    "BETWEEN",
    "JOIN",
    "ON",
    "AS",
    "GROUP",
    "BY",
    "ORDER",
    "ASC",
    "DESC",
    "LIMIT",
    "HAVING",
    "COUNT",
    "AVG",
    "SUM",
    "MIN",
    "MAX",
    "DISTINCT",
    "NULL",
    "TRUE",
    "FALSE",
    "UNION",
    "INTERSECT",
    "EXCEPT",
    "CASE",
    "WHEN",
    "THEN",
    "ELSE",
    "END",
}

COMPARISON_OPERATORS = ("=", "!=", "<>", ">", "<", ">=", "<=", "LIKE")


def parse_schema_identifiers(
    schema_text: str,
) -> tuple[set[str], dict[str, str], dict[str, list[str]]]:
    """Extract tables and columns from serialized schema text.

    Returns:
        all_tables: set of lowercase table names.
        all_columns: dict mapping lowercase column name to canonical column name.
        tables_dict: dict mapping canonical table name to list of canonical column names.
    """
    tables_dict: dict[str, list[str]] = {}
    current_table: str | None = None

    for line in schema_text.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("table:"):
            current_table = trimmed.split(":", 1)[1].strip()
            tables_dict[current_table] = []
        elif trimmed.startswith("- ") and current_table:
            col_part = trimmed[2:].split("[")[0].strip()
            if col_part:
                tables_dict[current_table].append(col_part)

    all_tables = {t.lower() for t in tables_dict}
    all_columns: dict[str, str] = {}
    for cols in tables_dict.values():
        for col in cols:
            all_columns[col.lower()] = col

    return all_tables, all_columns, tables_dict


def repair_sql(sql: str, schema_text: str, database_id: str = "") -> str:
    """Repair raw LSTM-generated SQL into valid, schema-consistent SQLite syntax."""
    del database_id
    if not sql or not sql.strip():
        return ""

    all_tables, all_columns, tables_dict = parse_schema_identifiers(schema_text)

    # 1. Clean whitespace around operators, punctuation, and aggregates
    repaired = re.sub(r"\b(COUNT|AVG|MIN|MAX|SUM)\s+\(", r"\1(", sql.strip(), flags=re.IGNORECASE)
    repaired = re.sub(r"\s*\.\s*", ".", repaired)
    repaired = re.sub(r"\(\s*", "(", repaired)
    repaired = re.sub(r"\s*\)", ")", repaired)
    repaired = re.sub(r"\s*,\s*", ", ", repaired)
    repaired = re.sub(r"\s+;", ";", repaired)
    repaired = re.sub(r"\s*;\s*$", "", repaired)

    # 2. Strip dangling trailing clauses or operators
    repaired = re.sub(r"\s+WHERE\s*$", "", repaired, flags=re.IGNORECASE)
    repaired = re.sub(r"\s+(?:AND|OR)\s*$", "", repaired, flags=re.IGNORECASE)
    repaired = re.sub(r"\s+(?:ORDER\s+BY|GROUP\s+BY)\s*$", "", repaired, flags=re.IGNORECASE)
    repaired = re.sub(r"\s*=\s*$", " = 1", repaired)

    # 3. WikiSQL single-table specialization: if schema has exactly one table, simplify FROM/JOIN
    if len(tables_dict) == 1:
        sole_table = next(iter(tables_dict.keys()))
        # Remove table aliases like 't1.' or 't2.'
        repaired = re.sub(r"\b[tT][0-9]\s*\.\s*", "", repaired)
        # Collapse multi-table JOINs into single table
        repaired = re.sub(
            r"FROM\s+.*?(?=\s+WHERE|\s+GROUP|\s+ORDER|\s+LIMIT|$)",
            f'FROM "{sole_table}"',
            repaired,
            flags=re.IGNORECASE,
        )

    # 4. Multi-table Spider table validation:
    elif all_tables:
        from_match = re.search(r"\bFROM\s+([A-Za-z0-9_]+)", repaired, flags=re.IGNORECASE)
        if from_match:
            from_t_raw = from_match.group(1)
            from_t = from_t_raw.lower()
            if from_t not in all_tables:
                # Hallucinated table name — align with table sharing most column tokens
                sql_lower = repaired.lower()
                best_t = max(
                    tables_dict.keys(),
                    key=lambda t: sum(1 for c in tables_dict[t] if c.lower() in sql_lower),
                )
                repaired = re.sub(
                    r"\bFROM\s+" + re.escape(from_t_raw) + r"\b",
                    f"FROM {best_t}",
                    repaired,
                    count=1,
                    flags=re.IGNORECASE,
                )
            elif "JOIN" not in repaired.upper():
                # Single-table query: check if selected columns actually belong to another table
                sql_tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", repaired.lower()))
                curr_cols = {c.lower() for c in tables_dict.get(from_t_raw, [])}
                curr_match_count = len(sql_tokens & curr_cols)
                best_t = max(
                    tables_dict.keys(),
                    key=lambda t: len(sql_tokens & {c.lower() for c in tables_dict[t]}),
                )
                best_match_count = len(sql_tokens & {c.lower() for c in tables_dict[best_t]})
                if best_match_count > curr_match_count + 1:
                    repaired = re.sub(
                        r"\bFROM\s+" + re.escape(from_t_raw) + r"\b",
                        f"FROM {best_t}",
                        repaired,
                        count=1,
                        flags=re.IGNORECASE,
                    )

    # 5. Token-level literal quoting in comparison predicates
    tokens = repaired.split()
    repaired_tokens: list[str] = []
    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        repaired_tokens.append(tok)
        if tok in COMPARISON_OPERATORS and idx + 1 < len(tokens):
            val = tokens[idx + 1]
            clean_val = val.rstrip(",;")
            trailing = val[len(clean_val) :]

            is_numeric = False
            try:
                float(clean_val)
                is_numeric = True
            except ValueError:
                pass

            is_col = clean_val.lower() in all_columns or any(
                clean_val.lower().endswith("." + c) for c in all_columns
            )
            is_keyword = clean_val.upper() in SQL_KEYWORDS
            is_already_quoted = (clean_val.startswith("'") and clean_val.endswith("'")) or (
                clean_val.startswith('"') and clean_val.endswith('"')
            )

            if (
                not is_numeric
                and not is_col
                and not is_keyword
                and not is_already_quoted
                and not clean_val.startswith("(")
            ):
                val = f"'{clean_val}'" + trailing

            repaired_tokens.append(val)
            idx += 2
            continue
        idx += 1

    repaired = " ".join(repaired_tokens)

    # 6. Double-quote multi-word column names that appear unquoted
    for col_raw in all_columns.values():
        if (
            (" " in col_raw or "/" in col_raw or "-" in col_raw)
            and col_raw in repaired
            and f'"{col_raw}"' not in repaired
        ):
            repaired = re.sub(rf"\b{re.escape(col_raw)}\b", f'"{col_raw}"', repaired)

    # 7. Balance unmatched parentheses
    open_count = repaired.count("(")
    close_count = repaired.count(")")
    if open_count > close_count:
        repaired += ")" * (open_count - close_count)

    return repaired
