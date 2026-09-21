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
        lowered = question.lower()
        conditions = self._extract_conditions(question, table)
        projection_question = re.split(
            r"\b(?:where|with|whose|that|which have|who have)\b",
            question,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        column = self._choose_column(projection_question, table)

        if re.search(r"\b(how many|number of|count)\b", lowered):
            expression = "COUNT(*)"
        else:
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
                    if re.search(rf"\b{re.escape(keyword)}\b", lowered)
                ),
                None,
            )
            expression = (
                f"{aggregate}({self._quote(column.name)})"
                if aggregate
                else self._quote(column.name)
            )

        query = f"SELECT {expression} FROM {self._quote(table.name)}"
        if conditions:
            query += " WHERE " + " AND ".join(
                f"{self._quote(column_name)} {operator} {self._quote_literal(value)}"
                for column_name, operator, value in conditions
            )
        return query

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
            _TableChoice(
                table,
                sum(cls._word_matches(part, words) for part in table.name.lower().split("_")),
            )
            for table in schema.tables
        ]
        return max(choices, key=lambda choice: (choice.score, -schema.tables.index(choice.table))).table

    @classmethod
    def _choose_column(cls, question: str, table: TableSpec) -> ColumnSpec:
        words = set(re.findall(r"[a-z0-9_]+", question.lower()))
        matches = [
            (cls._column_match_score(column.name, words), -index, column)
            for index, column in enumerate(table.columns)
        ]
        best = max(matches, default=(0, 0, None))
        if best[0]:
            return best[2]
        if not table.columns:
            raise ValueError(f"table has no columns: {table.name}")
        return table.columns[0]

    @staticmethod
    def _column_match_score(column_name: str, question_words: set[str]) -> int:
        normalized = column_name.lower().replace("_", " ")
        tokens = normalized.split()
        if normalized in question_words:
            return 3
        if len(tokens) > 1 and all(token in question_words for token in tokens):
            return 3
        if normalized.endswith("s") and normalized[:-1] in question_words:
            return 2
        if normalized + "s" in question_words:
            return 2
        if "_" not in column_name and normalized in question_words:
            return 2
        return 0

    @classmethod
    def _extract_conditions(
        cls, question: str, table: TableSpec
    ) -> list[tuple[str, str, str]]:
        """Extract the small comparison vocabulary used by WikiSQL questions."""
        normalized_question = question
        if any(column.name.lower() == "age" for column in table.columns):
            normalized_question = re.sub(
                r"\b(older|younger)\s+than\b",
                r"age \1 than",
                normalized_question,
                flags=re.IGNORECASE,
            )
        if any(column.name.lower() in {"country", "nation"} for column in table.columns):
            normalized_question = re.sub(
                r"\bfrom\s+(?P<value>[A-Za-z][A-Za-z -]*?)(?=[?.!,]|$)",
                r"country from \g<value>",
                normalized_question,
                count=1,
                flags=re.IGNORECASE,
            )
        conditions: list[tuple[int, str, str, str]] = []
        operators = (
            (r"(?:is\s+)?not\s+equal\s+to|is\s+not", "!="),
            (r"(?:is\s+)?at\s+least|(?:is\s+)?no\s+less\s+than", ">="),
            (r"(?:is\s+)?at\s+most|(?:is\s+)?no\s+more\s+than", "<="),
            (r"greater\s+than|more\s+than|older\s+than|over|above", ">"),
            (r"less\s+than|fewer\s+than|under|below", "<"),
            (r"equals?|is|are|in|from|=", "="),
        )
        for column in table.columns:
            aliases = [re.escape(column.name).replace("_", r"[\s_]+")]
            alias = rf"(?:{'|'.join(aliases)})"
            for operator_pattern, operator in operators:
                pattern = (
                    rf"(?P<column>\b{alias}\b)\s*(?:{operator_pattern})\s*"
                    r"(?P<value>[^,;?.!]+?)(?=\s+\b(?:and|or|where)\b|[,;?.!]|$)"
                )
                match = re.search(pattern, normalized_question, flags=re.IGNORECASE)
                if match:
                    value = match.group("value").strip().strip("\"'")
                    if value:
                        conditions.append(
                            (match.start(), column.name, operator, value)
                        )
                    break
        conditions.sort(key=lambda item: item[0])
        return [(name, operator, value) for _, name, operator, value in conditions]

    @staticmethod
    def _word_matches(word: str, question_words: set[str]) -> int:
        normalized = word.replace("_", " ").lower()
        tokens = normalized.split()
        if normalized in question_words or any(token in question_words for token in tokens):
            return 1
        if any(token.endswith("s") and token[:-1] in question_words for token in tokens):
            return 1
        if any(token + "s" in question_words for token in tokens):
            return 1
        return 0

    @staticmethod
    def _quote(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    @staticmethod
    def _quote_literal(value: str) -> str:
        if re.fullmatch(r"-?\d+(?:\.\d+)?", value):
            return value
        return "'" + value.replace("'", "''") + "'"
