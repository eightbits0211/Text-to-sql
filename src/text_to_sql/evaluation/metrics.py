"""Deterministic SQL evaluation for SQLite databases."""

import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from ..data.contracts import ExampleRecord


@dataclass(frozen=True)
class Prediction:
    example_id: str
    model_name: str
    predicted_sql: str


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    columns: tuple[str, ...] = ()
    rows: tuple[tuple[object, ...], ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class ExampleEvaluation:
    """Per-example outcome.

    ``exact_match`` is a normalized *string* match (whitespace collapsed,
    lowercased); it is not Spider's component-wise exact-set match.
    ``execution_match`` is the strict comparator: result-column labels
    (case-insensitive) and row order must agree. ``execution_match_official``
    follows the official Spider/test-suite semantics: column labels are
    ignored and rows are compared as a multiset unless the gold SQL has
    ``ORDER BY``.
    """

    example_id: str
    exact_match: bool
    execution_match: bool
    invalid_sql: bool
    failure_category: str | None
    execution_match_official: bool = False
    error_class: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class EvaluationReport:
    evaluated_count: int
    exact_match_accuracy: float
    execution_accuracy: float
    invalid_sql_rate: float
    examples: tuple[ExampleEvaluation, ...]

    @property
    def execution_accuracy_official(self) -> float:
        count = len(self.examples)
        return (
            sum(item.execution_match_official for item in self.examples) / count if count else 0.0
        )


def normalize_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip()).lower()


def classify_sqlite_error(message: str | None) -> str | None:
    """Map an SQLite error message to a coarse, report-friendly error class."""
    if message is None:
        return None
    text = message.lower()
    if text.startswith("no such column"):
        return "no_such_column"
    if text.startswith("no such table"):
        return "no_such_table"
    if text.startswith("ambiguous column"):
        return "ambiguous_column"
    if "syntax error" in text or text.startswith("unrecognized token"):
        return "syntax_error"
    if text.startswith("incomplete input"):
        return "incomplete_input"
    if "misuse of aggregate" in text or "aggregate functions are not allowed" in text:
        return "aggregate_misuse"
    if text == "sql is empty":
        return "empty_prediction"
    if text.startswith("only read queries"):
        return "forbidden_statement"
    return "other"


def _rows_match_official(gold: ExecutionResult, predicted: ExecutionResult, ordered: bool) -> bool:
    if len(gold.columns) != len(predicted.columns):
        return False
    if ordered:
        return gold.rows == predicted.rows
    return Counter(map(repr, gold.rows)) == Counter(map(repr, predicted.rows))


def execute_read_only(sql: str, database_path: Path) -> ExecutionResult:
    if not sql.strip():
        return ExecutionResult(status="invalid_sql", error="SQL is empty")
    if not re.match(r"^\s*(select|with)\b", sql, flags=re.IGNORECASE):
        return ExecutionResult(status="forbidden_statement", error="Only read queries are allowed")
    try:
        connection = sqlite3.connect(f"file:{database_path.resolve()}?mode=ro", uri=True)
    except sqlite3.Error as error:
        return ExecutionResult(status="database_error", error=str(error))
    # Some Spider databases (e.g. wta_1) store latin-1 bytes in TEXT columns;
    # decode leniently so gold and predicted queries are compared, not crashed.
    connection.text_factory = lambda value: value.decode("utf-8", errors="replace")
    try:
        cursor = connection.execute(sql)
        rows = tuple(tuple(row) for row in cursor.fetchall())
        columns = tuple(description[0] for description in cursor.description or ())
        return ExecutionResult(status="success", columns=columns, rows=rows)
    except sqlite3.OperationalError as error:
        return ExecutionResult(status="invalid_sql", error=str(error))
    except sqlite3.Error as error:
        return ExecutionResult(status="database_error", error=str(error))
    finally:
        connection.close()


def evaluate_predictions(
    examples: tuple[ExampleRecord, ...],
    predictions: tuple[Prediction, ...],
) -> EvaluationReport:
    prediction_map = {prediction.example_id: prediction for prediction in predictions}
    evaluated: list[ExampleEvaluation] = []
    for example in examples:
        prediction = prediction_map.get(example.example_id)
        predicted_sql = prediction.predicted_sql if prediction else ""
        exact_match = bool(predicted_sql.strip()) and normalize_sql(predicted_sql) == normalize_sql(
            example.gold_sql
        )
        gold_result = execute_read_only(example.gold_sql, example.database_path)
        predicted_result = execute_read_only(predicted_sql, example.database_path)
        execution_match = (
            gold_result.status == "success"
            and predicted_result.status == "success"
            and tuple(column.lower() for column in gold_result.columns)
            == tuple(column.lower() for column in predicted_result.columns)
            and gold_result.rows == predicted_result.rows
        )
        execution_match_official = (
            gold_result.status == "success"
            and predicted_result.status == "success"
            and _rows_match_official(
                gold_result,
                predicted_result,
                ordered=bool(re.search(r"\border\s+by\b", example.gold_sql, re.IGNORECASE)),
            )
        )
        failure_category = None
        if not predicted_sql.strip():
            failure_category = "empty_prediction"
        elif predicted_result.status != "success":
            failure_category = predicted_result.status
        elif not execution_match:
            failure_category = "wrong_result"
        evaluated.append(
            ExampleEvaluation(
                example_id=example.example_id,
                exact_match=exact_match,
                execution_match=execution_match,
                invalid_sql=predicted_result.status != "success",
                failure_category=failure_category,
                execution_match_official=execution_match_official,
                error_class=classify_sqlite_error(predicted_result.error),
                error_message=predicted_result.error,
            )
        )
    count = len(evaluated)
    return EvaluationReport(
        evaluated_count=count,
        exact_match_accuracy=sum(item.exact_match for item in evaluated) / count if count else 0.0,
        execution_accuracy=sum(item.execution_match for item in evaluated) / count
        if count
        else 0.0,
        invalid_sql_rate=sum(item.invalid_sql for item in evaluated) / count if count else 0.0,
        examples=tuple(evaluated),
    )
