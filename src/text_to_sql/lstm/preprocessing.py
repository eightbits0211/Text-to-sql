"""Deterministic tokenization and training-only vocabulary helpers."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from ..data.contracts import DatasetSplit, ExampleRecord

SPECIAL_TOKENS = ("<pad>", "<unk>", "<bos>", "<eos>", "<schema_sep>")
SQL_KEYWORDS = {
    "SELECT",
    "FROM",
    "WHERE",
    "ORDER",
    "BY",
    "LIMIT",
    "GROUP",
    "HAVING",
    "COUNT",
    "AVG",
    "MAX",
    "MIN",
    "SUM",
    "DISTINCT",
    "AS",
    "AND",
    "OR",
    "NOT",
    "IN",
    "IS",
    "NULL",
    "LIKE",
    "CASE",
    "WHEN",
    "THEN",
    "ELSE",
    "END",
    "JOIN",
    "LEFT",
    "RIGHT",
    "OUTER",
    "INNER",
    "ON",
    "UNION",
    "INTERSECT",
    "EXCEPT",
    "ASC",
    "DESC",
}
SQL_OPERATORS = ("(", ")", ",", ".", ";", ":", "=", "<", ">", "<=", ">=", "!=", "<>", "+", "-", "*", "/", "%")
QUESTION_SCHEMA_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+(?:\.[0-9]+)?")
SQL_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+(?:\.[0-9]+)?|<=|>=|!=|<>|[=<>+/*%\-(),.;:]|'[^']*'|\"[^\"]*\"")


def _normalize_token(token: str) -> str:
    text = token.strip()
    if not text:
        return ""
    if text.startswith(("'", '"')) and text.endswith(("'", '"')) and len(text) >= 2:
        return text.lower()
    return text.lower()


def _iter_surface_tokens(text: str, pattern: re.Pattern[str]) -> list[str]:
    return [match.group(0) for match in pattern.finditer(text)]


def tokenize_question(question: str) -> list[str]:
    """Return deterministic question tokens in a stable, lowercase canonical form."""
    return [_normalize_token(token) for token in _iter_surface_tokens(question, QUESTION_SCHEMA_TOKEN_RE)]


def tokenize_schema(schema_text: str) -> list[str]:
    """Deterministically tokenize the existing schema serialization."""
    return [_normalize_token(token) for token in _iter_surface_tokens(schema_text, QUESTION_SCHEMA_TOKEN_RE)]


def tokenize_sql(sql: str) -> list[str]:
    """Return a deterministic SQL token sequence with keyword casing normalized."""
    tokens: list[str] = []
    for token in _iter_surface_tokens(sql, SQL_TOKEN_RE):
        if token.startswith(("'", '"')) and token.endswith(("'", '"')) and len(token) >= 2:
            tokens.append(_normalize_token(token))
        elif token.upper() in SQL_KEYWORDS:
            tokens.append(token.upper())
        elif token in SQL_OPERATORS:
            tokens.append(token)
        else:
            tokens.append(_normalize_token(token))
    return tokens


@dataclass(frozen=True)
class TokenizedExample:
    question_tokens: tuple[str, ...]
    schema_tokens: tuple[str, ...]
    sql_tokens: tuple[str, ...]
    source_tokens: tuple[str, ...]


def tokenize_example(example: ExampleRecord) -> TokenizedExample:
    question_tokens = tuple(tokenize_question(example.question))
    schema_tokens = tuple(tokenize_schema(example.schema_text))
    sql_tokens = tuple(tokenize_sql(example.gold_sql))
    source_tokens = tuple(question_tokens + schema_tokens)
    return TokenizedExample(
        question_tokens=question_tokens,
        schema_tokens=schema_tokens,
        sql_tokens=sql_tokens,
        source_tokens=source_tokens,
    )


@dataclass(frozen=True)
class FixedVocabulary:
    tokens: tuple[str, ...]
    token_to_index: dict[str, int]
    counts: dict[str, int]

    def get_index(self, token: str) -> int | None:
        if token in self.token_to_index:
            return self.token_to_index[token]
        normalized = _normalize_token(token)
        if normalized in self.token_to_index:
            return self.token_to_index[normalized]
        if token.upper() in self.token_to_index:
            return self.token_to_index[token.upper()]
        return None

    def __contains__(self, token: str) -> bool:
        return self.get_index(token) is not None

    def __len__(self) -> int:
        return len(self.tokens)


def build_training_vocabulary(
    examples: list[ExampleRecord] | tuple[ExampleRecord, ...],
    *,
    max_size: int | None = None,
) -> FixedVocabulary:
    """Build a fixed vocabulary from train-split examples only."""
    counts: Counter[str] = Counter()
    for token in SPECIAL_TOKENS:
        counts[token] = 1
    for token in SQL_KEYWORDS:
        counts[token] = max(counts.get(token, 0), 1)
    for token in SQL_OPERATORS:
        counts[token] = max(counts.get(token, 0), 1)

    for example in examples:
        if example.split != DatasetSplit.TRAIN:
            continue
        for token in tokenize_example(example).question_tokens + tokenize_example(example).schema_tokens + tokenize_example(example).sql_tokens:
            counts[token] += 1

    ordered = sorted(counts, key=lambda token: (-counts[token], token))
    if max_size is not None:
        ordered = ordered[:max_size]
    tokens = tuple(ordered)
    return FixedVocabulary(
        tokens=tokens,
        token_to_index={token: index for index, token in enumerate(tokens)},
        counts=dict(counts),
    )


@dataclass(frozen=True)
class PreprocessingEvent:
    token: str
    normalized: str
    reason: str = "unresolvable_target_token"


@dataclass(frozen=True)
class TargetResolution:
    index: int
    token: str
    event: PreprocessingEvent | None = None


@dataclass(frozen=True)
class CopyTarget:
    source_tokens: tuple[str, ...]
    extended_tokens: tuple[str, ...]
    source_positions: dict[str, tuple[int, ...]]
    source_to_index: dict[str, int]
    copy_index_by_token: dict[str, int]


def build_copy_target(example: ExampleRecord, vocabulary: FixedVocabulary) -> CopyTarget:
    """Build the example-specific extended vocabulary and source-position map."""
    raw_source_tokens = _iter_surface_tokens(example.question, QUESTION_SCHEMA_TOKEN_RE) + _iter_surface_tokens(
        example.schema_text,
        QUESTION_SCHEMA_TOKEN_RE,
    )
    source_tokens = tuple(raw_source_tokens)
    source_positions: defaultdict[str, list[int]] = defaultdict(list)
    source_to_index: dict[str, int] = {}
    copy_index_by_token: dict[str, int] = {}
    extended_tokens = list(vocabulary.tokens)

    for position, token in enumerate(source_tokens):
        normalized = _normalize_token(token)
        if not normalized:
            continue
        source_positions[normalized].append(position)
        vocab_index = vocabulary.get_index(token)
        if vocab_index is not None:
            source_to_index[normalized] = vocab_index
            continue
        if normalized not in copy_index_by_token:
            copy_index_by_token[normalized] = len(extended_tokens)
            extended_tokens.append(token)
        source_to_index[normalized] = copy_index_by_token[normalized]

    return CopyTarget(
        source_tokens=source_tokens,
        extended_tokens=tuple(extended_tokens),
        source_positions={key: tuple(value) for key, value in source_positions.items()},
        source_to_index=source_to_index,
        copy_index_by_token=copy_index_by_token,
    )


def resolve_target_token(
    token: str,
    vocabulary: FixedVocabulary,
    copy_target: CopyTarget,
) -> TargetResolution:
    """Resolve a target token against the fixed vocabulary and copy targets."""
    vocab_index = vocabulary.get_index(token)
    if vocab_index is not None:
        return TargetResolution(index=vocab_index, token=token)
    normalized = _normalize_token(token)
    if normalized in copy_target.source_to_index:
        return TargetResolution(index=copy_target.source_to_index[normalized], token=token)
    fallback_index = vocabulary.token_to_index.get("<unk>", 0)
    event = PreprocessingEvent(token=token, normalized=normalized)
    return TargetResolution(index=fallback_index, token="<unk>", event=event)


__all__ = [
    "SPECIAL_TOKENS",
    "SQL_KEYWORDS",
    "SQL_OPERATORS",
    "CopyTarget",
    "FixedVocabulary",
    "PreprocessingEvent",
    "TargetResolution",
    "TokenizedExample",
    "build_copy_target",
    "build_training_vocabulary",
    "resolve_target_token",
    "tokenize_example",
    "tokenize_question",
    "tokenize_schema",
    "tokenize_sql",
]
