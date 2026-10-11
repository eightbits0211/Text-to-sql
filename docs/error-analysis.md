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

- **Abstentions:** the template returns an empty prediction for 92 of 1,034 dev questions and
  208 of 2,147 test questions. Every abstention counts as invalid SQL.
- **Quoting fix:** the template used to double-quote every identifier (`FROM "singer"`). The
  official parser reads that as a string value, so the template scored 0% official EM. It now
  quotes only when necessary. Its real official EM is 5.9% on dev and 6.7% on test, and its
  official EX is unchanged at 9.9% and 9.5%.
- **Execution-match audit:** execution hits without a string match are classified automatically
  from signatures; see the report, section d.9.

## 6a. Copy gate (measured, `scripts/measure_copy_gate.py`)

No training target *requires* copying, because every Spider-train token is in the vocabulary.
The copy gate still learns, since copying an in-vocabulary source token also produces the
correct token. On 200 dev questions (teacher-forced), at copy-only gold positions the gate
chooses to copy 96% of the time (mean p_gen 0.04). But it puts only 0.17 probability on the
correct source token, versus 0.82 for in-vocabulary targets. So the model knows *when* to copy,
but not *what*: a schema-linking failure.

## 7. WikiSQL: a harness defect, then a rendering defect

**Harness defect (fixed).** The official `dev.db` stores columns as `col0..colN`, with
lower-cased text values. Our loader wrote gold SQL with header names (`SELECT "Position" ...`).
SQLite reads a double-quoted name that matches no column as a string literal, so gold queries ran
without error but compared constants. 6,007/8,415 dev gold queries returned an empty result, and
any prediction that also returned nothing counted as correct. All earlier WikiSQL EX numbers
(template 7.23%, LSTM 0.04%) were therefore meaningless.

The harness now runs a per-example `execution_prelude`: a TEMP VIEW named after the table that
exposes `colN` under its header, with text compared case-insensitively as in the official
executor. 7,767 gold queries now return real answers, and the 388 empty ones are known
annotation noise. The gold-equals-gold sanity check could not catch this, because gold
trivially equals gold.

**Rendering defect.** Job 361547 scored WikiSQL with `wikisql_checkpoint.pt`, saved before any
Spider training, so this is not catastrophic forgetting. Unquoted multi-word headers and split
literals made the output unexecutable.

| WikiSQL dev (8,415), corrected harness | Strict EX | Invalid |
|---|---:|---:|
| LSTM Stage-1, raw | 3.11% | 89.5% |
| LSTM Stage-1, base decoding (Job 361547) | 5.76% | 81.1% |
| LSTM Stage-1, final decoding | 17.15% | 32.5% |
| Template | 2.65% | 0.0% |

Final vs template: 1,399 vs 179 discordant questions (McNemar p ≈ 1e-234). The remaining
invalid queries are mostly hallucinated multi-word column names from other training tables
(`points for`, `year born`), which are schema-linking errors.

## 8. Qualitative cases

See report §4.10 for six labelled cases: correct, execution-equivalent, projection
omission, type-token leak turned wrong column, aggregation error, and join hallucination.
