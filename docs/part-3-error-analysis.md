# Part 3 Error Analysis (Spider dev, 1,034 questions)

Produced with `scripts/analyze_part2.py` (model-agnostic) and `scripts/official_stats.py`.
Raw outputs: `$TEXT2SQL_DATA_ROOT/part3/analysis/spider-dev/analysis.{json,md}` and
`$TEXT2SQL_DATA_ROOT/part3/analysis/dev_stats.json`. Dev was used for checkpoint
selection, so these figures are slightly optimistic; headline claims use the test split.

Systems: T5-base beam-8 (job 398846, epoch-14 checkpoint), T5-base + A + B
(schema-constrained beams, EXPLAIN check, execution rerank), gpt-oss-20b 0-shot (job 398898).

## Headline (official evaluator)

| System | EX | EM | Invalid SQL |
|---|---:|---:|---:|
| T5-base beam | 54.1% | 52.1% | 30.7% |
| T5-base + A + B | 64.4% | 59.5% | 13.1% |
| gpt-oss-20b 0-shot | 78.6% | 20.1% | 0.8% |

A + B vs beam: +10.3 EX, 95% database-clustered CI [7.5, 13.3], Holm-adjusted
McNemar p = 1e-27. It fixes 110 questions and breaks 3.

## By query structure (strict EX)

| System | Single table (544) | Multi-table join (438) | Other (52) |
|---|---:|---:|---:|
| T5-base beam | 68.2% | 25.6% | 57.7% |
| T5-base + A + B | 73.5% | 39.7% | 59.6% |
| gpt-oss-20b 0-shot | 45.2% | 44.5% | 46.2% |

The novelty helps joins most (+14.1 vs +5.3 on single-table questions): join
queries reference more identifiers, so they have more chances to name a column
or table that does not exist. gpt-oss's strict EX is flat across structures
because strict EX penalizes its column aliases everywhere (official EX ignores
labels; see below).

## Invalid SQL by SQLite error

| Error | T5 beam | T5 + A + B | gpt-oss |
|---|---:|---:|---:|
| no such column | 275 | 123 | 3 |
| no such table | 21 | 7 | 0 |
| syntax error / incomplete | 17 | 4 | 1 |
| non-SELECT output | 0 | 0 | 4 |

Unknown columns dominate T5's invalid output, matching the Part 2 finding that
schema linking is the main failure. A + B removes 55% of them.

## Root cause of failures (first failing component)

| Root cause | T5 beam | T5 + A + B | gpt-oss |
|---|---:|---:|---:|
| invalid SQL | 317 | 135 | 8 |
| wrong table set | 44 | 80 | 69 |
| wrong columns | 68 | 98 | 114 |
| wrong clause structure | 20 | 31 | 68 |
| wrong values | 12 | 11 | 67 |
| same SQL signature as gold | 58 | 72 | 216 |

- **A + B turns invalid SQL into valid SQL, not always correct SQL.** Wrong-table
  and wrong-column failures rise because some formerly invalid queries now
  execute but answer the wrong question. Execution feedback cannot detect these.
- **gpt-oss fails semantically, not syntactically.** Its largest bucket (216)
  has the same SQL skeleton as gold: mostly column aliases, column order and
  value formatting that strict comparison rejects and the official evaluator
  partly accepts. Its 20.1% EM against 78.6% EX shows exact match is unfit for
  LLM output that is correct but stylistically different from Spider's gold.

## Metric limitations seen here

- **EM understates LLMs:** gpt-oss is 58.5 points lower on EM than on EX.
- **EX can overstate:** a query can return the right rows by coincidence.
  "EM-confirmed EX" (both correct) is the conservative bound: T5 + A + B 56.6%.
- **Strict vs official EX:** strict EX (column labels and row order must match)
  cuts gpt-oss from 72.4% to 45.5% on our harness; official semantics ignore labels.

## Qualitative examples

1. *"List singer names and number of concerts for each singer."* (concert_singer)
   - beam: `... FROM concert AS T1 JOIN singer AS T2 ON T1.singer_id = ...` (no such column)
   - A + B: `... FROM singer_in_concert AS T1 JOIN singer AS T2 ...` (correct; demo Case 4)
2. *"How much does the youngest dog weigh?"* (pets_1)
   - beam: `SELECT weight FROM pets ORDER BY age LIMIT 1` (`age` is in Student, not Pets)
   - A + B: `SELECT weight FROM pets ORDER BY pet_age LIMIT 1` (correct)
3. *"Which of the countries has the most car makers?"* (car_1)
   - beam: `SELECT CountryName FROM car_makers ...` (CountryName lives in countries)
   - A + B: adds the join to `countries` (correct)
4. Execution false positive, *"Find the last name of the student who has a cat that is age 3."*
   (pets_1): A + B produces `... WHERE T2.pet_age = 3 AND T2.pet_age = 3`, dropping the
   pet-type condition, yet it is scored correct by EX. The only pet aged 3 in the database is a
   cat, so the wrong query returns the gold answer (`Smith`) by coincidence. EM rejects it.
   This is the "EX can overstate" limitation in practice, and why EM-confirmed EX is reported.
