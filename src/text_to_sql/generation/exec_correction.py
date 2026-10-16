"""Novelty B: execution-guided correction.

- ``execution_rerank`` (T5): run the k beam candidates in order and keep the
  first that executes; with ``prefer_nonempty`` a candidate returning rows beats
  one returning nothing. An empty result is never treated as proof of
  correctness, only as weaker evidence than a non-empty one.
- ``correction_loop`` (LLM): if the SQL fails, send the SQLite error back to
  the model and ask for a fix, at most ``max_retries`` times.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..evaluation.metrics import ExecutionResult, execute_read_only

# Candidates are run only to choose between them, so the budget is short.
RERANK_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class RerankResult:
    sql: str
    chosen_index: int
    statuses: tuple[str, ...]


def execution_rerank(
    candidates: list[str],
    database_path: Path,
    prelude: tuple[str, ...] = (),
    prefer_nonempty: bool = True,
    timeout_seconds: float = RERANK_TIMEOUT_SECONDS,
) -> RerankResult:
    """Pick a candidate by execution; falls back to the top beam if none execute."""
    if not candidates:
        return RerankResult("", -1, ())
    statuses: list[str] = []
    first_success: int | None = None
    for index, sql in enumerate(candidates):
        result = execute_read_only(sql, database_path, prelude, timeout_seconds)
        if result.status != "success":
            statuses.append(result.status)
            continue
        statuses.append("success" if result.rows else "empty")
        if first_success is None:
            first_success = index
        if result.rows or not prefer_nonempty:
            return RerankResult(sql, index, tuple(statuses))
    chosen = first_success if first_success is not None else 0
    return RerankResult(candidates[chosen], chosen, tuple(statuses))


@dataclass(frozen=True)
class CorrectionResult:
    sql: str
    attempts: int
    final_status: str
    errors: tuple[str, ...]


def correction_message(sql: str, result: ExecutionResult) -> str:
    return (
        f"Your query\n```sql\n{sql}\n```\nfailed in SQLite with the error: {result.error}\n"
        "Fix the query. Use only tables and columns from the schema. "
        "Reply with the corrected SQL only, inside a ```sql code block."
    )


def correction_loop(
    generate: Callable[[list[dict[str, str]]], str],
    extract: Callable[[str], str],
    messages: list[dict[str, str]],
    database_path: Path,
    max_retries: int = 2,
    prelude: tuple[str, ...] = (),
) -> CorrectionResult:
    """Generate, execute, and feed errors back until the SQL runs or retries run out.

    Stops early on success (including an empty result: the loop repairs
    errors, it does not judge answers) and returns the last attempt otherwise.
    """
    conversation = list(messages)
    errors: list[str] = []
    sql, status = "", "invalid_sql"
    for attempt in range(1, max_retries + 2):
        response = generate(conversation)
        sql = extract(response)
        result = execute_read_only(sql, database_path, prelude, RERANK_TIMEOUT_SECONDS)
        status = result.status
        if status == "success":
            return CorrectionResult(sql, attempt, status, tuple(errors))
        errors.append(result.error or status)
        conversation += [
            {"role": "assistant", "content": response},
            {"role": "user", "content": correction_message(sql, result)},
        ]
    return CorrectionResult(sql, max_retries + 1, status, tuple(errors))
