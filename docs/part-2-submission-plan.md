# Part 2 Submission Plan — Text-to-SQL

**Internal implementation deadline:** September 30, 2026  
**Official course deadline:** October 15, 2026, 23:55 IST  
**Assessment:** Part 2, 20 marks  
**Scope:** Baseline system, preliminary results, report sections, and live demo

## 1. Part 2 objective

Deliver a reliable, demonstrable Text-to-SQL baseline that satisfies the
course requirements without depending on the unfinished Part 3 transformer or
novelty component.

By September 30, the team must have a frozen baseline, reproducible metrics,
error analysis, and a working demo. October 1–15 is reserved for verification,
report polishing, packaging, and submission—not for starting new core features.

## 2. Part 2 acceptance criteria

### Required system behavior

- Load and validate the WikiSQL warm-up data.
- Load at least a usable Spider subset or the full Spider data if feasible.
- Serialize schema information consistently.
- Train or fit one classical baseline.
- Generate one SQL candidate for each input.
- Execute predictions against SQLite without terminating on individual failures.
- Report exact-match accuracy, execution accuracy, and invalid-SQL rate.
- Show the complete demo flow: question → generated SQL → result/error.

### Required evidence

- Dataset description, source, size, structure, limitations, and preprocessing.
- Literature survey covering Text-to-SQL and the selected baseline approach.
- Baseline architecture and implementation details.
- Hyperparameters and compute environment.
- Preliminary metrics on held-out data.
- Error analysis with quantitative categories and representative examples.
- Reproducible commands and configuration.
- A report draft covering Sections a–d from the course instructions:
  introduction, literature survey, dataset, and method/initial experiments.

## 3. Deliberately reduced Part 2 scope

The following remain explicitly deferred to Part 3:

- Fine-tuned transformer model as the main modern system.
- Constrained decoding or execution-error self-correction.
- Novelty ablations.
- BIRD evaluation.
- Production-style deployment and conversational memory.

An additive CPU-fallback LSTM seq2seq baseline is now included in the Part 2
comparison plan. It does not replace the deterministic template baseline and
must not block the Part 2 submission if compute constraints prevent comparable
results. Its architecture and validation gates are specified in
[`lstm-baseline-design.md`](./lstm-baseline-design.md).

The Part 2 baseline must still be designed behind an interface that will allow
the Part 3 model to use the same evaluation and demo layers.

## 4. Recommended implementation choices

### Classical baseline

Use the deterministic template/grammar baseline as the stable primary baseline.
Add the LSTM seq2seq model as a secondary trainable baseline after its design
checkpoint is reviewed. The template baseline should support a bounded but
explicit subset such as:

- SELECT columns
- Single-table filtering
- Basic comparison operators
- AND/OR conditions
- Optional ORDER BY and LIMIT where supported

Unsupported questions must return an empty candidate or a clearly recorded
unsupported result; they must not be silently reported as successful queries.
The LSTM must use the same prediction adapter and evaluation path so the two
baselines can be compared without changing metric definitions.

### Dataset order

1. WikiSQL subset for the end-to-end smoke test.
2. A small Spider development slice for cross-domain and join behavior.
3. Full required evaluation only after the pipeline is stable.

### Interface

Build a CLI first because it is the lowest-risk demo surface. Add Gradio or
Streamlit only if the CLI is stable before the internal deadline.

## 5. Granular work breakdown

### Workstream A — Repository and reproducibility

- Create the source layout described in the main PRD.
- Add a dependency manifest and environment setup instructions.
- Add a single configuration format for paths, seeds, limits, and output paths.
- Define artifact directories for datasets, checkpoints, predictions, metrics,
  logs, and demo assets.
- Add a run manifest containing command, configuration, timestamp, seed, and
  software version information.

**Done when:** A new environment can run a documented smoke-test command.

### Workstream B — Data loading and schema serialization

- Implement WikiSQL ingestion.
- Implement Spider ingestion.
- Validate required fields and database paths.
- Serialize tables, columns, types, primary keys, and foreign keys.
- Preserve dataset split assignments.
- Add deterministic sampling for smoke tests.
- Record excluded-example counts and split statistics.
- Label examples as single-table or multi-table join.

**Done when:** A sample record can be printed and every required field is
non-empty and traceable to its source database.

### Workstream C — Classical baseline

- Define the supported SQL grammar/template inventory.
- Implement question parsing and schema matching.
- Implement SQL rendering with safe identifier handling.
- Return one candidate string for every example.
- Return an empty candidate for unsupported inputs.
- Save predictions with question, schema/database ID, gold SQL, predicted SQL,
  and failure reason.

**Done when:** The baseline runs end-to-end on WikiSQL smoke data and a Spider
smoke slice without crashing.

### Workstream D — Evaluation harness

- Implement documented SQL normalization for exact match.
- Implement SQLite execution for gold and predicted queries.
- Compare result tables deterministically.
- Count empty, invalid, schema-error, and execution-error predictions.
- Continue evaluation after per-example errors.
- Produce aggregate metrics and breakdown tables.
- Produce machine-readable JSON/CSV and human-readable Markdown/HTML output.

**Done when:** A fixed prediction file always produces the same metrics.

### Workstream E — Error analysis

- Categorize failures as schema linking, syntax, join path, aggregation,
  unsupported construction, empty output, or other.
- Break down metrics by dataset split and query difficulty.
- Break down metrics by single-table versus join structure.
- Select representative successes and failures.
- Record whether execution accuracy may be a false positive.
- Create at least one table and one qualitative example suitable for the report.

**Done when:** The report can explain recurring weaknesses rather than only
listing one overall score.

### Workstream F — CLI/demo

- Add database selection or a documented default database.
- Display the available schema or schema summary.
- Accept a natural-language question.
- Print generated SQL.
- Validate before execution.
- Print a result table for valid SQL.
- Print an explicit error for invalid or unsupported SQL.
- Add at least three scripted demo examples: easy, filter, and failure case.

**Done when:** The complete demo can be run from one documented command.

### Workstream G — Part 2 report and presentation

- Draft introduction and motivation.
- Add literature survey with primary sources.
- Add dataset and preprocessing details with statistics/examples.
- Add baseline architecture and implementation details.
- Add metrics and limitations.
- Add preliminary results and error analysis.
- Add reproducibility instructions.
- Prepare a 5–8 minute demo script and viva questions.

**Done when:** A reader can reproduce the baseline and understand its limits.

## 6. Timeline

Dates use the current project date of September 21, 2026 and IST.

| Date | Focus | Required output | Gate |
|---|---|---|---|
| Sep 21 | Scope lock and setup | Part 2 branch/PR workflow, environment, config skeleton, task ownership | No new Part 2 features after scope lock without approval |
| Sep 22 | Data contracts | WikiSQL/Spider record schema, path configuration, sample fixtures | Sample record contract reviewed |
| Sep 23 | WikiSQL ingestion | Loader, validation, deterministic smoke split, statistics | WikiSQL smoke command passes |
| Sep 24 | Schema serialization | Tables, columns, types, keys, foreign keys, serialization tests | Serialized schema snapshots reviewed |
| Sep 25 | Spider ingestion | Spider loader, split handling, sampled evaluation slice | Spider smoke command passes |
| Sep 26 | Baseline core | Template/grammar parser and SQL renderer | One prediction produced per input |
| Sep 27 | Baseline integration | End-to-end WikiSQL baseline run and artifacts | No crash on supported/unsupported examples |
| Sep 28 | Evaluation harness | Exact match, execution accuracy, invalid-SQL rate | Fixed-fixture metric tests pass |
| Sep 29 | Error analysis and demo | Breakdown tables, failure examples, CLI flow | Demo run completed from clean command |
| Sep 30 | Internal freeze | Baseline checkpoint, metrics, report draft, demo recording/script | **Part 2 implementation complete** |
| Oct 1–3 | Verification | Clean-environment rerun, metric audit, data/artifact checks | Reproduction run matches recorded metrics |
| Oct 4–6 | Report completion | Literature, preprocessing examples, results, limitations | Report review pass |
| Oct 7–9 | Demo hardening | Error handling, scripted examples, fallback assets, viva preparation | Demo works without manual code edits |
| Oct 10–12 | Packaging | Final PDF/LaTeX export, source archive, README, commands | Submission package review |
| Oct 13–14 | Final QA | Rubric checklist, formatting, citations, final dry run | No unresolved critical issue |
| Oct 15 | Submission | Upload report and required artifacts before 23:55 IST | Official submission complete |

## 7. Daily execution loop

Each work session should follow this order:

1. Select one bounded task from the work breakdown.
2. Define its acceptance check before implementation.
3. Implement the smallest complete vertical slice.
4. Run targeted tests or a smoke command.
5. Save metrics/logs/artifacts outside source files.
6. Update the task status and note blockers.
7. Open or update a PR; do not merge directly to the main branch.

## 8. Required artifacts by September 30

```text
docs/part-2-submission-plan.md
docs/part-2-report-outline.md
README.md or equivalent setup instructions
configs/part2-smoke.*
data/README.md or dataset acquisition instructions
src/data/
src/models/
src/evaluation/
src/demo/
tests/
artifacts/part2/
```

The exact source filenames may vary, but the functional artifacts must exist.
Large datasets, model checkpoints, generated predictions, and secrets must not
be committed to the repository.

## 9. Part 2 checklist

- [x] Scope and internal deadline confirmed.
- [x] Environment setup is documented.
- [x] Dataset acquisition instructions are reproducible.
- [x] WikiSQL smoke pipeline passes.
- [x] Spider smoke pipeline passes.
- [ ] Schema serialization includes required relations.
- [x] Classical baseline returns one candidate per input.
- [ ] Unsupported/invalid outputs are explicitly counted.
- [x] Exact-match implementation is tested.
- [x] Execution accuracy implementation is tested.
- [x] Invalid-SQL rate implementation is tested.
- [x] Metrics are reproducible from saved predictions.
- [ ] Error analysis tables and examples are prepared.
- [x] CLI or GUI demo runs from one command.
- [ ] Report sections a–d are complete.
- [x] Clean-environment verification passes.
- [ ] Final PR is reviewed before submission.

## 10. Stop/go rules

- **Go to Spider full evaluation** only after the WikiSQL smoke pipeline and
  evaluator pass.
- **Go to demo polish** only after baseline predictions and metrics are saved.
- **Do not start Part 3 modeling before Sep 30** if it threatens the Part 2 gate.
- **Cut scope** to a documented Spider smoke slice rather than ship an unstable
  full-data pipeline.
- **Escalate a blocker** when it remains unresolved for one working day or
  threatens the Sep 30 internal freeze.

## 11. Current checkpoint status

As of September 21, the baseline, evaluation harness, report breakdowns, CLI,
typed configuration, and dataset-layout instructions are implemented and
validated on synthetic fixtures. Real WikiSQL and Spider smoke execution is
intentionally **not marked complete** until the datasets are supplied through
the documented environment variables. This prevents empty-path runs from being
reported as benchmark results.

The next execution gate is:

1. Configure approved local WikiSQL and Spider paths.
2. Run `uv run python scripts/run_part2_smoke.py`.
3. Inspect prediction and evaluation artifacts under the configured output
   directory.
4. Update this plan, checklist, and progress log with retained/excluded counts
   and metrics.

## 12. Dataset smoke checkpoint

The official WikiSQL archive and official Yale Spider release have now been
downloaded outside the repository and extracted successfully. The bounded
smoke run used five development examples from each dataset:

| Dataset | Retained | Excluded | Execution accuracy |
|---|---:|---:|---:|
| WikiSQL | 5 | 0 | 0.0000 |
| Spider | 5 | 0 | 0.4000 |

These are template-baseline smoke results, not final benchmark claims. The
WikiSQL zero score identifies the next engineering task: improve question
parsing and condition rendering. Spider's 0.4000 execution accuracy confirms
that the loader and evaluator can recognize equivalent result tables. Result
column labels are compared case-insensitively; row order remains
order-sensitive until a separate policy is approved. Archive checksums and
source URLs are stored in the external dataset manifest, not in Git.

## 13. Authority alignment and remaining Part 2 work

The current implementation is aligned with the authoritative course
description and evaluation requirements for the **Part 2 baseline stage**:

| Requirement area | Current status |
|---|---|
| Dataset selection and justification | Covered: Spider primary, WikiSQL warm-up, sources and citations documented |
| Classical baselines | Covered: deterministic template baseline; additive LSTM design checkpoint completed and implementation gated on review |
| Schema/data processing | Covered: official loaders, typed records, schema serialization, exclusions |
| Evaluation | Covered: exact match, execution accuracy, invalid-SQL rate, breakdown reports |
| Error analysis | Partially covered: quantitative breakdowns exist; report-ready examples remain |
| Demonstration | Covered technically: CLI question → SQL → result/error |
| Report evidence | Outstanding: sections, citations, statistics, and polished error analysis |
| Modern transformer model and novelty | Intentionally deferred to Part 3 |

The project is therefore consistent with the PDFs at the current milestone,
but it must not be presented as the complete course project yet. Remaining
Part 2 work is primarily quality and evidence work:

1. Improve baseline coverage beyond the five-example smoke slice.
2. Save a larger reproducible run manifest and metric artifacts.
3. Add three scripted demo cases and rehearse them from a clean environment.
4. Draft and review the required report sections and preliminary error analysis.
5. Freeze Part 2 scope on September 30 and open the final review PR only after
   user approval.

## 14. Baseline quality checkpoint

The deterministic baseline now supports simple projection selection, equality
and comparison conditions, multiple `AND` conditions, common aggregations, and
limited natural-language age/country phrasing. On a bounded official
development slice of 25 examples per dataset, the current smoke results are:

| Dataset | Retained | Excluded | Execution accuracy |
|---|---:|---:|---:|
| WikiSQL | 25 | 0 | 0.0800 |
| Spider | 25 | 0 | 0.0800 |

These are preliminary baseline results, not final benchmark claims. The next
gate is a larger reproducible run with a manifest and report-ready error
analysis.
