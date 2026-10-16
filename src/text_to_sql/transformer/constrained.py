"""Novelty A: schema-constrained beam search for T5 (a lightweight PICARD).

Two parts, ablated separately:

1. ``SchemaConstraintProcessor`` (in-search): after every step each beam's
   prefix is lexed; if a *completed* bare word is not a SQL keyword, a table or
   column of the target database, a declared alias, a number, or a word from
   the question, the beam is pruned (all its next-token scores set to -inf).
   Quoted strings are skipped, so literal values are never constrained.
2. ``explain_valid`` (post-search): SQLite ``EXPLAIN`` compiles a finished
   candidate without running it, which catches syntax errors and references to
   missing tables or columns; the first candidate that compiles is returned.

Unlike PICARD this needs no incremental SQL parser: it works on words, so it
cannot reject ill-formed clause order, only unknown identifiers. That is the
error class the Part 2 analysis found dominant (schema linking).
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import torch

from .serialization import parse_schema_text

SQL_KEYWORDS = frozenset(
    [
        "select",
        "from",
        "where",
        "group",
        "by",
        "order",
        "having",
        "limit",
        "offset",
        "join",
        "inner",
        "left",
        "right",
        "outer",
        "cross",
        "natural",
        "on",
        "using",
        "as",
        "and",
        "or",
        "not",
        "in",
        "is",
        "null",
        "like",
        "glob",
        "between",
        "exists",
        "distinct",
        "all",
        "union",
        "intersect",
        "except",
        "asc",
        "desc",
        "case",
        "when",
        "then",
        "else",
        "end",
        "cast",
        "count",
        "sum",
        "avg",
        "min",
        "max",
        "abs",
        "length",
        "lower",
        "upper",
        "round",
        "substr",
        "instr",
        "coalesce",
        "ifnull",
        "nullif",
        "date",
        "datetime",
        "julianday",
        "strftime",
        "typeof",
        "total",
        "group_concat",
        "true",
        "false",
        "integer",
        "text",
        "real",
        "numeric",
        "varchar",
    ]
)

_STRING = re.compile(r"'(?:[^']|'')*'?|\"(?:[^\"]|\"\")*\"?")
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_ALIAS_DECL = re.compile(r"\bas\s+([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)
_TABLE_ALIAS = re.compile(r"^t\d+$")


def allowed_words(schema_text: str, question: str) -> frozenset[str]:
    """Lowercased bare words a query over this schema/question may contain."""
    parsed = parse_schema_text(schema_text)
    words = set(SQL_KEYWORDS)
    for table, columns in parsed.tables:
        words.add(table.lower())
        words.update(column.lower() for column in columns)
    words.update(word.lower() for word in _WORD.findall(question))
    return frozenset(words)


def invalid_word(prefix: str, allowed: frozenset[str]) -> str | None:
    """First completed bare word in ``prefix`` that is not allowed, else None.

    The trailing word is ignored while it may still be growing (no delimiter
    after it yet), so a beam is never pruned mid-identifier.
    """
    unquoted = _STRING.sub(" ", prefix)
    aliases = {match.lower() for match in _ALIAS_DECL.findall(unquoted)}
    words = list(_WORD.finditer(unquoted))
    if words and words[-1].end() == len(unquoted):
        words = words[:-1]
    for match in words:
        start = match.start()
        if start > 0 and unquoted[start - 1].isdigit():
            continue  # e.g. the "e" in 1e5
        word = match.group(0).lower()
        if word in allowed or word in aliases or _TABLE_ALIAS.match(word):
            continue
        return match.group(0)
    return None


class SchemaConstraintProcessor:
    """HF ``LogitsProcessor`` pruning beams that mention unknown identifiers.

    Works for one example at a time (``batch_size == 1``), with any beam count.
    ``prefix_tokens`` is the number of decoder-start tokens to skip.
    """

    def __init__(self, tokenizer, schema_text: str, question: str, prefix_tokens: int = 1):
        self.tokenizer = tokenizer
        self.allowed = allowed_words(schema_text, question)
        self.prefix_tokens = prefix_tokens
        self.pruned = 0

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor):
        texts = self.tokenizer.batch_decode(
            input_ids[:, self.prefix_tokens :], skip_special_tokens=True
        )
        for row, text in enumerate(texts):
            if invalid_word(text, self.allowed) is not None:
                scores[row, :] = -float("inf")
                self.pruned += 1
        return scores


def explain_valid(sql: str, database_path: Path) -> bool:
    """True if SQLite can compile ``sql`` against the database (nothing is executed)."""
    if not sql.strip():
        return False
    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    try:
        connection.execute(f"EXPLAIN {sql}")
        return True
    except (sqlite3.Error, sqlite3.Warning):
        return False
    finally:
        connection.close()


def first_valid(candidates: list[str], database_path: Path) -> str:
    """First candidate that compiles; falls back to the top beam so a prediction is never lost."""
    for sql in candidates:
        if explain_valid(sql, database_path):
            return sql
    return candidates[0] if candidates else ""
