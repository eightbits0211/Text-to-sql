"""Surface-form rendering of decoded LSTM tokens into SQL text.

The tokenizer lowercases every token and stores quoted SQL literals as one
unquoted token (``'United States'`` -> ``united states``). Joining decoded
tokens with spaces therefore loses (a) literal case, (b) literal boundaries,
and (c) the exact spelling of schema identifiers such as WikiSQL's
``School/Club Team``. This module restores all three from the question and
the serialized schema, without changing what the model predicted.
"""

from __future__ import annotations

import re

from .preprocessing import QUESTION_SCHEMA_TOKEN_RE, SQL_KEYWORDS
from .sql_repair import parse_schema_identifiers

VALUE_OPERATORS = frozenset({"=", "!=", "<>", "<", ">", "<=", ">=", "LIKE"})
_PLAIN_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_NUMBER = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?$")
_ALIAS = re.compile(r"^t[0-9]+$", re.IGNORECASE)

# Tokens introduced by ``serialize_schema`` (markup and column types). They are
# copyable from the encoder input but are never valid SQL unless the schema
# really has a table or column with that name.
SCHEMA_MARKUP_TOKENS = frozenset(
    {
        "database",
        "table",
        "columns",
        "foreign_keys",
        "primary",
        "key",
        "text",
        "number",
        "time",
        "boolean",
        "others",
        "real",
        "integer",
        "int",
        "varchar",
    }
)


def schema_name_map(schema_text: str) -> dict[str, str]:
    """Lowercase table/column name -> canonical spelling from the schema."""
    _, all_columns, tables_dict = parse_schema_identifiers(schema_text)
    names = {table.lower(): table for table in tables_dict}
    for lowered, canonical in all_columns.items():
        names.setdefault(lowered, canonical)
    return names


def blocked_markup_tokens(schema_text: str) -> frozenset[str]:
    """Markup/type tokens that are not real identifiers in this schema."""
    names = schema_name_map(schema_text)
    return frozenset(token for token in SCHEMA_MARKUP_TOKENS if token not in names)


def _quote_identifier(name: str) -> str:
    if _PLAIN_IDENTIFIER.match(name):
        return name
    return '"' + name.replace('"', '""') + '"'


def _find_in_question(words: list[str], question: str) -> str | None:
    """Return the question substring spelling ``words`` (case-insensitive)."""
    if not words:
        return None
    pattern = r"\W*".join(re.escape(word) for word in words)
    match = re.search(rf"(?<!\w){pattern}(?!\w)", question, flags=re.IGNORECASE)
    return match.group(0) if match else None


def _render_literal(token: str, question: str) -> str:
    """Render a value token as a single-quoted literal with question casing."""
    core = token.strip("%")
    prefix = "%" if token.startswith("%") else ""
    suffix = "%" if token.endswith("%") and len(token) > 1 else ""
    words = QUESTION_SCHEMA_TOKEN_RE.findall(core)
    surface = _find_in_question(words, question) if words else None
    if surface is None and core:
        surface = core
    text = f"{prefix}{surface or ''}{suffix}"
    return "'" + text.replace("'", "''") + "'"


def render_sql(tokens: list[str], question: str, schema_text: str) -> str:
    """Join decoded tokens into SQL, restoring identifier and literal surface forms."""
    names = schema_name_map(schema_text)
    rendered: list[str] = []
    previous = ""
    for token in tokens:
        lowered = token.lower()
        if token.upper() in SQL_KEYWORDS:
            piece = token.upper()
        elif (
            previous in VALUE_OPERATORS
            and lowered not in names
            and token not in {"(", "*", "-"}
            and not _NUMBER.match(token)
            and not _ALIAS.match(token)
        ):
            piece = _render_literal(token, question)
        elif lowered in names:
            piece = _quote_identifier(names[lowered])
        else:
            piece = token
        rendered.append(piece)
        previous = piece.upper() if piece.upper() in SQL_KEYWORDS else piece
    return " ".join(rendered)


__all__ = [
    "SCHEMA_MARKUP_TOKENS",
    "blocked_markup_tokens",
    "render_sql",
    "schema_name_map",
]
