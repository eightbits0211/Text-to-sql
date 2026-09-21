"""A deterministic, schema-aware template baseline for Part 2."""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from ..data.contracts import ExampleRecord
from ..data.schema import ColumnSpec, DatabaseSchema, TableSpec
from ..evaluation.metrics import EvaluationReport, Prediction, evaluate_predictions


@dataclass(frozen=True)
class _TableChoice:
    table: TableSpec
    score: int


class TemplateBaseline:
    """Generate simple SQL using lexical question/schema matching.

    This baseline is intentionally deterministic and dependency-free. It is
    suitable for smoke tests and establishes the shared model adapter used by
    later neural baselines.
    """

    name = "template-baseline"

    def fit(self, examples: Iterable[ExampleRecord]) -> "TemplateBaseline":
        """Keep the adapter compatible with trainable baselines.

        The deterministic baseline has no learned parameters, but consuming
        the examples makes its lifecycle interchangeable with later models.
        """
        tuple(examples)
        return self

    def predict(self, question: str, schema: DatabaseSchema | str) -> str:
        if not question.strip():
            raise ValueError("question must not be empty")
        database_schema = self._coerce_schema(schema)
        table = self._choose_table(question, database_schema)
        column = self._choose_column(question, table)
        lowered = question.lower()

        if re.search(r"\b(how many|number of|count)\b", lowered):
            return f"SELECT COUNT(*) FROM {self._quote(table.name)}"

        aggregate = next(
            (
                function
                for keyword, function in (
                    ("average", "AVG"),
                    ("avg", "AVG"),
                    ("mean", "AVG"),
                    ("maximum", "MAX"),
                    ("max", "MAX"),
                    ("minimum", "MIN"),
                    ("min", "MIN"),
                    ("total", "SUM"),
                    ("sum", "SUM"),
                )
                if keyword in lowered
            ),
            None,
        )
        if aggregate:
            return (
                f"SELECT {aggregate}({self._quote(column.name)}) "
                f"FROM {self._quote(table.name)}"
            )

        return f"SELECT {self._quote(column.name)} FROM {self._quote(table.name)}"

    def predict_record(self, example: ExampleRecord) -> Prediction:
        return Prediction(
            example_id=example.example_id,
            model_name=self.name,
            predicted_sql=self.predict(example.question, example.schema_text),
        )

    def predict_records(self, examples: Iterable[ExampleRecord]) -> tuple[Prediction, ...]:
        return tuple(self.predict_record(example) for example in examples)

    def evaluate(
        self,
        examples: Iterable[ExampleRecord],
        database_root: object | None = None,
    ) -> EvaluationReport:
        del database_root
        records = tuple(examples)
        return evaluate_predictions(records, self.predict_records(records))

    @staticmethod
    def _coerce_schema(schema: DatabaseSchema | str) -> DatabaseSchema:
        if isinstance(schema, DatabaseSchema):
            return schema
        if not schema.strip():
            raise ValueError("schema must not be empty")
        tables: list[TableSpec] = []
        current_table: str | None = None
        columns = []
        for line in schema.splitlines():
            if line.startswith("table: "):
                if current_table is not None:
                    tables.append(TableSpec(current_table, tuple(columns)))
                current_table = line.removeprefix("table: ").strip()
                columns = []
            elif line.startswith("  - ") and current_table is not None:
                match = re.match(r"\s+-\s+(.+?)\s+\[([^\]]+)\]", line)
                if match:
                    columns.append(ColumnSpec(match.group(1), match.group(2)))
        if current_table is not None:
            tables.append(TableSpec(current_table, tuple(columns)))
        if not tables:
            raise ValueError("schema does not contain a parseable table")
        return DatabaseSchema("unknown", tuple(tables))

    @classmethod
    def _choose_table(cls, question: str, schema: DatabaseSchema) -> TableSpec:
        words = set(re.findall(r"[a-z0-9_]+", question.lower()))
        choices = [
            _TableChoice(table, sum(part in words for part in table.name.lower().split("_")))
            for table in schema.tables
        ]
        return max(choices, key=lambda choice: (choice.score, -schema.tables.index(choice.table))).table

    @classmethod
    def _choose_column(cls, question: str, table: TableSpec):
        lowered = question.lower()
        for column in table.columns:
            if column.name.lower() in lowered:
                return column
        if not table.columns:
            raise ValueError(f"table has no columns: {table.name}")
        return table.columns[0]

    @staticmethod
    def _quote(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'
