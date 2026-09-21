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
    supported_sql_features = (
        "single-table SELECT",
        "COUNT(*)",
        "AVG, MAX, MIN, and SUM over one column",
        "single- and multi-column projection",
        "DISTINCT projection",
        "AND-connected comparison predicates",
        "ORDER BY and LIMIT",
    )
    unsupported_sql_features = (
        "joins",
        "subqueries",
        "set operations",
        "GROUP BY and HAVING",
        "OR-connected predicates",
    )

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
        projection_question = re.split(
            r"\b(?:order(?:ed)?|sort)\s+by\b|\b(?:top|first|last)\s+\d+\b",
            projection_question,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        columns = self._choose_columns(projection_question, table)
        aggregates = self._extract_aggregates(lowered, columns, table)
        if re.search(r"\b(how many|number of|count)\b", lowered):
            expressions = ["COUNT(*)"]
        elif aggregates:
            expressions = [
                f"{function}({self._quote(column.name)})"
                for function, column in aggregates
            ]
        else:
            expressions = [self._quote(column.name) for column in columns]

        distinct = "DISTINCT " if re.search(r"\b(?:distinct|unique)\b", lowered) else ""
        query = f"SELECT {distinct}{', '.join(expressions)} FROM {self._quote(table.name)}"
        if conditions:
            query += " WHERE " + " AND ".join(
                f"{self._quote(column_name)} {operator} {self._quote_literal(value)}"
                for column_name, operator, value in conditions
            )
        order = self._extract_order(question, table)
        if order:
            column, direction, limit = order
            query += f" ORDER BY {self._quote(column.name)} {direction}"
            if limit is not None:
                query += f" LIMIT {limit}"
        else:
            limit = self._extract_limit(question)
            if limit is not None:
                query += f" LIMIT {limit}"
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
        columns = cls._choose_columns(question, table)
        return columns[0]

    @classmethod
    def _choose_columns(cls, question: str, table: TableSpec) -> list[ColumnSpec]:
        words = set(re.findall(r"[a-z0-9_]+", question.lower()))
        answer_hint = re.split(
            r"\b(?:is|are|does|do|was|were|on|from|for)\b",
            question,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        hint_words = set(re.findall(r"[a-z0-9_]+", answer_hint.lower()))
        matches = [
            (
                cls._column_match_score(column.name, words, question)
                + (5 if cls._column_match_score(column.name, hint_words, answer_hint) else 0),
                -index,
                column,
            )
            for index, column in enumerate(table.columns)
        ]
        if not table.columns:
            raise ValueError(f"table has no columns: {table.name}")
        positive = [match for match in matches if match[0] > 0]
        if not positive:
            return [table.columns[0]]
        positive.sort(reverse=True)
        # A conjunction in the answer phrase is a reliable WikiSQL cue for
        # projecting more than one column.  Do not include predicate columns.
        answer_words = re.split(
            r"\b(?:where|whose|that|with)\b", question, 1, flags=re.IGNORECASE
        )[0]
        selected = [
            column for score, _, column in positive
            if re.search(
                rf"\b{re.escape(column.name)}\b", answer_words, re.IGNORECASE
            )
            or cls._column_match_score(column.name, set(re.findall(r"[a-z0-9_]+", answer_words.lower())), answer_words) >= 3
        ]
        if len(selected) < 2 or not re.search(
            r"\band\b|,", answer_words, re.IGNORECASE
        ):
            return [positive[0][2]]
        return sorted(
            set(selected),
            key=lambda column: (
                cls._column_mention_position(column.name, answer_words),
                table.columns.index(column),
            ),
        )

    @staticmethod
    def _column_mention_position(column_name: str, question: str) -> int:
        aliases = (column_name, column_name.replace("_", " "))
        positions = [
            position
            for alias in aliases
            if (position := question.lower().find(alias.lower())) >= 0
        ]
        return min(positions, default=len(question))

    @staticmethod
    def _column_match_score(
        column_name: str, question_words: set[str], question: str = ""
    ) -> int:
        normalized = column_name.lower().replace("_", " ")
        tokens = normalized.split()
        if normalized in question_words:
            return 4
        if len(tokens) > 1 and all(token in question_words for token in tokens):
            return 4
        if normalized.endswith("s") and normalized[:-1] in question_words:
            return 3
        if normalized + "s" in question_words:
            return 3
        if normalized.endswith("y") and normalized[:-1] + "ies" in question_words:
            return 3
        aliases = {
            "no.": {"number", "no", "#"},
            "number": {"no", "no."},
            "player": {"person", "people"},
            "name": {"names"},
        }
        if any(alias in question_words for alias in aliases.get(normalized, set())):
            return 2
        if "_" not in column_name and normalized in question_words:
            return 2
        return 0

    @classmethod
    def _extract_aggregates(
        cls, lowered: str, columns: list[ColumnSpec], table: TableSpec
    ) -> list[tuple[str, ColumnSpec]]:
        keywords = (
            (("average", "avg", "mean"), "AVG"),
            (("maximum", "max", "highest", "largest"), "MAX"),
            (("minimum", "min", "lowest", "smallest"), "MIN"),
            (("total", "sum"), "SUM"),
        )
        found: list[tuple[int, str]] = []
        for words, function in keywords:
            for word in words:
                match = re.search(rf"\b{re.escape(word)}\b", lowered)
                if match:
                    found.append((match.start(), function))
                    break
        found.sort()
        if not found:
            return []
        result = []
        for index, function in found:
            context = lowered[max(0, index - 50): index + 80]
            column = cls._choose_column(context, table)
            result.append((function, column))
        return result or [(found[0][1], columns[0])]

    @classmethod
    def _extract_limit(cls, question: str) -> int | None:
        match = re.search(
            r"\b(?:top|first|last)\s+(\d+)\b|\blimit\s+(\d+)\b",
            question,
            re.IGNORECASE,
        )
        return int(next(group for group in match.groups() if group)) if match else None

    @classmethod
    def _extract_order(
        cls, question: str, table: TableSpec
    ) -> tuple[ColumnSpec, str, int | None] | None:
        match = re.search(
            r"\b(?:order(?:ed)?|sort)\s+by\s+(?P<column>.+?)(?=$|[,.;])",
            question,
            re.IGNORECASE,
        )
        direction = "ASC"
        if match:
            column_text = match.group("column").strip()
            direction_match = re.search(
                r"\s+(ascending|descending|asc|desc)$", column_text, re.IGNORECASE
            )
            if direction_match:
                direction = "DESC" if direction_match.group(1).lower().startswith("desc") else "ASC"
                column_text = column_text[:direction_match.start()]
            else:
                range_match = re.search(
                    r"\bfrom\s+(?:the\s+)?(oldest|youngest|earliest|latest)\s+to\s+"
                    r"(?:the\s+)?(oldest|youngest|earliest|latest)\b",
                    column_text,
                    re.IGNORECASE,
                )
                if range_match:
                    direction = (
                        "DESC"
                        if range_match.group(1).lower() in {"oldest", "latest"}
                        else "ASC"
                    )
                    column_text = column_text[:range_match.start()]
            column = cls._choose_column(column_text, table)
            return column, direction, cls._extract_limit(question)
        match = re.search(
            r"\b(highest|largest|lowest|smallest)\b", question, re.IGNORECASE
        )
        if match:
            direction = "DESC" if match.group(1).lower() in {"highest", "largest"} else "ASC"
            return cls._choose_column(question[:match.start()] or question, table), direction, cls._extract_limit(question)
        match = re.search(
            r"\b(oldest|youngest|earliest|latest)\b"
            r"(?:\s+\w+){0,3}\s+\b(to|through|until)\b\s+"
            r"\b(oldest|youngest|earliest|latest)\b",
            question,
            re.IGNORECASE,
        )
        if match:
            first = match.group(1).lower()
            direction = "DESC" if first in {"oldest", "latest"} else "ASC"
            return cls._choose_column(question, table), direction, cls._extract_limit(question)
        return None

    @classmethod
    def _extract_conditions(
        cls, question: str, table: TableSpec
    ) -> list[tuple[str, str, str]]:
        """Extract the small comparison vocabulary used by WikiSQL questions."""
        if re.search(r"\bor\b", question, re.IGNORECASE):
            # OR requires parenthesized boolean logic; dropping all predicates
            # is safer than silently changing it to an AND query.
            return []
        normalized_question = re.sub(
            r"\bfrom\s+(?:the\s+)?(?:oldest|youngest|earliest|latest)\s+to\s+"
            r"(?:the\s+)?(?:oldest|youngest|earliest|latest)\b",
            "",
            question,
            flags=re.IGNORECASE,
        )
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
            normalized_name = column.name.lower().replace("_", " ")
            if normalized_name in {"no.", "no"}:
                aliases.extend((r"number", r"no\.?", r"#"))
            if normalized_name in {"school/club team", "team"}:
                aliases.extend((r"school(?:/club)?", r"team"))
            if normalized_name in {"player", "person", "name"}:
                aliases.extend((r"player", r"person", r"name"))
            alias = rf"(?:{'|'.join(aliases)})"
            for operator_pattern, operator in operators:
                pattern = (
                    rf"(?P<column>\b{alias}\b)\s*(?:{operator_pattern})\s*"
                    r"(?P<value>[^,;?.!]+?)(?=\s+\b(?:and|or|where|on|at)\b|[,;?.!]|$)"
                )
                match = re.search(pattern, normalized_question, flags=re.IGNORECASE)
                if match:
                    value = match.group("value").strip().strip("\"'")
                    if value:
                        conditions.append(
                            (match.start(), column.name, operator, value)
                        )
                    break
        # Questions such as "what team is Amir Johnson on?" omit an explicit
        # equality operator.  The subject noun still provides a safe link.
        for column in table.columns:
            if column.name.lower() in {"no.", "no"}:
                match = re.search(
                    r"\b(?:number|no\.?|#)\s+(?P<value>-?\d+)\b",
                    question,
                    re.IGNORECASE,
                )
                if match:
                    conditions.append((match.start(), column.name, "=", match.group("value")))
                    break
        for column in table.columns:
            if column.name.lower() not in {"player", "person", "name"}:
                continue
            match = re.search(
                r"\b(?:player|person|name)\s+(?P<value>[A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*)?)\s+(?:on|at|from)\b",
                question,
                re.IGNORECASE,
            )
            if match and not re.match(r"number\b", match.group("value"), re.IGNORECASE):
                conditions.append((match.start(), column.name, "=", match.group("value")))
                break
        if any(name.lower() in {"no.", "no"} for _, name, _, _ in conditions):
            conditions = [
                item for item in conditions
                if not re.search(r"\b(?:player|person)\s+number\b", item[3], re.IGNORECASE)
            ]
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
