# Baseline Error Analysis

Evidence for Section (d) of the Part 2 report ([`part-2-report.md`](part-2-report.md)).
All numbers here were recomputed by `scripts/analyze_part2.py` and `scripts/run_ablation.py`
from per-example prediction artifacts. The LSTM is the Job 361547 checkpoint
(`spider_checkpoint.pt`). "As submitted" is its original decoding; "final" adds the
schema-markup mask and surface-form rendering (`DecodeOptions()`).
Artifacts live outside Git under `/Users/roshini/datasets/text-to-sql/{ablation,analysis}/`.

## 1. Metric definitions (read first)

- **Official EM / EX:** from the official Spider evaluator (`taoyds/test-suite-sql-eval`).
  EM is component-wise exact-set match and ignores values. EX compares result multisets,
  and row order matters only when the gold SQL has `ORDER BY`.
- **Strict EX:** this repository's harness. Result-column labels and row order must match.
- **SM (normalised string match):** whitespace-collapsed, lower-cased string equality.
  Earlier documents called this "exact match". It is not Spider's EM.
- **Invalid:** any SQLite error or empty prediction.

## 2. Outcome distribution (Spider dev, 1,034)

| Outcome | As submitted | Final |
|---|---:|---:|
| SM and strict EX correct | 33 | 34 |
| Strict EX correct, SM wrong | 28 | 32 |
| Valid SQL, wrong result | 175 | 222 |
| Invalid SQL | 798 | 746 |

The original draft reported 803 invalid and 170 wrong-result for the as-submitted run.
The 5-query difference is a harness fix. Two `wta_1` gold queries and four predictions
crashed on non-UTF-8 text, and they are now decoded leniently.

## 3. Invalid SQL by SQLite error class (Spider dev)

| Error class | As submitted | Final |
|---|---:|---:|
| `no_such_column` | 708 | 690 |
| `syntax_error` | 55 | 29 |
| `incomplete_input` | 19 | 8 |
| `ambiguous_column` | 6 | 9 |
| `no_such_table` | 6 | 5 |
| `aggregate_misuse` | 3 | 4 |
| other | 1 | 1 |

In the as-submitted output, 278/1,034 predictions used the bare token `text` as an
identifier. `text` is a column *type* emitted by the schema serialiser (`- Country [text]`),
so it was copyable from the encoder input. It was the most frequent nonexistent column
(147 errors). The schema-markup mask removes it completely. Most of those queries then
become valid but still wrong, because the model picks another wrong column.

Most syntax errors in the as-submitted output came from repair v1 splitting multi-word
literals (`= 'united' states`). Rendering now keeps each literal as one quoted value.

## 4. Structural error taxonomy (Spider dev, final LSTM, 968 failures)

Each failure is compared with its gold query on literal-stripped signatures. A failure can
carry several labels.

| Error type | Count | Share |
|---|---:|---:|
| Referenced column set differs from gold | 958 | 99.0% |
| Wrong `FROM`/`JOIN` table set | 804 | 83.1% |
| Wrong number of joins | 421 | 43.5% |
| Wrong literal value(s) | 310 | 32.0% |
| Wrong aggregate function(s) | 167 | 17.3% |
| `WHERE` present/absent incorrectly | 117 | 12.1% |
| Nested subquery present/absent incorrectly | 109 | 11.3% |
| Wrong number of projected items | 107 | 11.1% |
| `GROUP BY` present/absent incorrectly | 103 | 10.6% |
| Set operation present/absent incorrectly | 55 | 5.7% |
| `LIMIT` / `ORDER BY` / `HAVING` mismatches | 45 / 41 / 27 | ≤ 4.6% |

**Schema linking** (identifiers referenced in predicted vs gold SQL): precision 39.9%,
recall 40.4%. Tables: precision 46.8%, recall 46.5%. The dominant failure is choosing
the wrong schema element, not SQL syntax.

## 5. Breakdown by slice (Spider dev, strict EX, Wilson 95% CI)

| Slice | n | LSTM final | Template |
|---|---:|---:|---:|
| Easy | 248 | 14.9% [11.0, 19.9] | 18.1% [13.8, 23.4] |
| Medium | 446 | 4.3% [2.7, 6.6] | 2.7% [1.5, 4.6] |
| Hard | 174 | 5.7% [3.2, 10.3] | 0.0% [0.0, 2.2] |
| Extra-hard | 166 | 0.0% [0.0, 2.3] | 1.8% [0.6, 5.2] |
| Single-table | 544 | 10.3% [8.0, 13.1] | 10.3% [8.0, 13.1] |
| Multi-table (join or set op) | 438 | 1.8% [0.9, 3.6] | 0.9% [0.4, 2.3] |
| Nested (other) | 52 | 3.8% [1.1, 13.0] | 0.0% [0.0, 6.9] |

The medium/hard non-monotonicity sits inside overlapping intervals and should not be
interpreted. Structure categories are defined in `data/spider.py::_query_structure`.
A query containing `JOIN`, `UNION`, `INTERSECT` or `EXCEPT` counts as multi-table, so set
operations land there even over a single table. Otherwise, more than one `SELECT` counts
as nested.

## 6. Template audit

- **Abstentions:** the current template code returns an empty prediction for 92/1,034
  dev questions. The Job 361547 revision of the template never abstained, and its
  strict EX was the same (60).
- **0% SM and 0% official EM are formatting artefacts.** The template double-quotes every
  identifier (`FROM "singer"`), which the official parser reads as a string literal. With
  identifier quotes removed, its official EM is 5.9% on dev and 6.7% on test.
- **Its 60 strict-EX hits without SM:** 43 structurally equivalent to gold, 11 coincidental
  with a gold clause missing, and 6 coincidental where the gold result is empty or zero.
  Example: `SELECT DISTINCT "Country" FROM "singer"` matches gold `... WHERE age > 20` only
  because every singer in the database is older than 20.

## 7. WikiSQL: rendering defect, not catastrophic forgetting

Job 361547 scored WikiSQL with `wikisql_checkpoint.pt`, saved before any Spider training.
The slurm log line is `Loading dataset-specific checkpoint: wikisql_checkpoint.pt`. The
0.04% EX therefore cannot come from Spider fine-tuning. The predictions are usually
sensible but unexecutable. For example, `SELECT player FROM "table_1_10015132_11" WHERE no.= 42`
should be `WHERE "No." = 42`. The problems were unquoted, lower-cased multi-word or
punctuated column names and split multi-word literals. Full-dev numbers with the
rendering fix are in report §4.11.

## 8. Qualitative cases

See report §4.10 for six labelled cases: correct, execution-equivalent, projection
omission, type-token leak turned wrong column, aggregation error, and join hallucination.
