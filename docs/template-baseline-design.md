# Template/Grammar Baseline Design

## Role

`TemplateBaseline` is the project's deterministic classical baseline. It is a
legitimate baseline option named in the project proposal and remains the
primary Part 2 fallback while the additive LSTM baseline is implemented and
validated.

The model is deliberately transparent rather than broadly expressive. Its
purpose is to establish a reproducible question-to-SQL baseline, provide a
stable evaluation contract, and make common schema-linking and parsing errors
measurable before neural models are introduced.

## Input and output contract

The baseline consumes:

- a non-empty natural-language question;
- a `DatabaseSchema` or the existing serialized `schema_text`.

It returns one quoted SQLite SQL string. The adapter also exposes `fit`,
`predict_record`, `predict_records`, and `evaluate` so it can be evaluated
through the same prediction and reporting pipeline as trainable models.

`fit` is intentionally a no-op: the parser has no learned parameters, but it
consumes the training records to preserve the lifecycle expected by later
baselines.

## Supported grammar

The parser supports a bounded single-table grammar:

```text
SELECT <column>
SELECT <column>, <column>, ...
SELECT COUNT(*)
SELECT {AVG|MAX|MIN|SUM}(<column>), ...
FROM <table>
[WHERE <column> {=|!=|>|<|>=|<=} <literal>
      [AND <column> {=|!=|>|<|>=|<=} <literal>]...]
[ORDER BY <column> [ASC|DESC] [LIMIT <n>]]
```

Question language covered by the current implementation includes:

- table-name and column-name lexical matches, including simple plurals;
- count/number questions;
- single-column projection questions;
- multi-column and `DISTINCT` projection questions;
- average, maximum, minimum, and total/sum wording;
- multiple aggregate expressions in one question;
- numeric and quoted string comparisons;
- common comparison paraphrases such as “older than”, “at least”, and
  “from <country>”;
- multiple predicates connected with `and`.
- ordering and top/first/last limits where the ordering column can be linked.

Identifiers are selected from the supplied schema and quoted for SQLite.
Literals are numeric when they match the supported numeric form and otherwise
escaped as SQL string literals.

## Explicit limitations

The current baseline does not claim support for joins, subqueries, set
operations, `GROUP BY`, `HAVING`, `ORDER BY`, `LIMIT`, or `OR` predicates.
When the wording falls outside the parser's rules, the result may be a
syntactically valid but semantically incorrect query; this is recorded as a
baseline limitation for error analysis rather than treated as neural-model
capability.

The evaluator remains responsible for validating and executing the generated
SQL. Per-example execution failures must not terminate an evaluation run.

## Determinism and evaluation

The parser has no random state or trainable parameters. Given the same
question and serialized schema, it produces the same SQL. Template and LSTM
experiments must use the same `ExampleRecord` inputs, SQLite execution policy,
exact-match normalization, prediction artifacts, and breakdown reports.

The baseline is evaluated on WikiSQL first and Spider second. Its results are
reported as bounded baseline evidence, not as a claim of complete Spider
coverage.

## Bounded evaluation evidence

The complete official development splits were evaluated with the shared
pipeline on 2026-09-21. WikiSQL retained 8,415 of 8,421 records and achieved
0.0723 execution accuracy, 0.0126 exact match, and 0.0000 invalid-SQL rate.
Spider retained all 1,034 records and achieved 0.0580 execution accuracy,
0.0000 exact match, and 0.0058 invalid-SQL rate. Spider single-table accuracy
was 0.1029, compared with 0.0091 for multi-table joins.

The complete report-ready metrics, predictions, breakdowns, and run manifest
are stored outside Git under
`/Users/roshini/datasets/text-to-sql/artifacts-template-full-dev/`. A fixed
250-example run remains available as a fast regression subset, but it is not
used as the headline benchmark because the released dev files are grouped
rather than demonstrably shuffled.
