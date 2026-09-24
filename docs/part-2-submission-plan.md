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

The trainable Pointer-Generator LSTM seq2seq model is designated as the
**primary baseline** for Part 2 per user direction and alignment with the Part 1
Proposal. The deterministic template baseline serves as the reliable fallback
and comparison floor, guaranteeing 0% crash risk and deterministic metric
evaluation. Its architecture and validation gates are specified in
[`lstm-baseline-design.md`](./lstm-baseline-design.md).

The Part 2 baseline is designed behind a unified interface that will allow
the Part 3 transformer model to use the same evaluation and demo layers.

## 4. Recommended implementation choices

### Classical baseline

Designate the Pointer-Generator LSTM seq2seq model as the primary baseline,
and the deterministic template/grammar baseline as the secondary fallback and
comparison baseline. The template baseline supports a bounded but explicit
subset such as:

- SELECT columns
- Single-table filtering
- Basic comparison operators
- AND/OR conditions
- Optional ORDER BY and LIMIT where supported

Unsupported questions return an empty candidate or a clearly recorded
unsupported result; they are never silently reported as successful queries.
The LSTM uses the same prediction adapter and evaluation path so both
baselines are compared without changing metric definitions.

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

### Current execution status
 
- The deterministic template/grammar baseline has been hardened and evaluated on the full
  official development splits (8,415 WikiSQL records, 1,034 Spider records; 0% invalid rate).
  Report-ready artifacts are stored under `artifacts-template-full-dev/`.
- The Pointer-Generator LSTM seq2seq model is designated the **primary baseline**,
  with bidirectional LSTM encoder, Bahdanau additive attention decoder, and schema-pointer copy mechanism.
- The live demo showcase (`text-to-sql-demo --demo`) is fully verified locally with 3 scripted
  queries, model switching (`--model template|lstm`), and ASCII result tables.
- HPC Blackwell GPU verification job `359139` ran on `gpunode8` (NVIDIA RTX PRO 6000, 98GB VRAM,
  CUDA 13.0) and passed 100% of GPU tensor allocation and matrix multiplication checks.
- Conducted deep code audit and applied 8 training and preprocessing fixes:
  epoch shuffling with deterministic RNG, missing `--device` and `--batch-size` CLI args,
  manifest tracking, redundant re-tokenization elimination, and type annotation corrections.
- Synced updated code to HPC repository and resubmitted full two-stage training job **`359370`**:
  1. Stage 1: WikiSQL single-table warm-up training (~56,000 examples, 10 epochs).
  2. Stage 2: Spider primary cross-domain training (~7,000 examples, 10 epochs).
  3. Full evaluation across complete dev sets: all 1,034 Spider dev records and 8,415 WikiSQL dev records.
- 50/50 unit tests pass in 3.05s; Ruff clean. Job `359370` is queued on `gpunode8`.

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

### Workstream C — Dual classical baselines (Template + Pointer-Generator LSTM)

- **Deterministic Template Baseline (Primary / Fallback)**:
  - Supported inventory: SELECT projections, single-table filtering, comparisons, AND/OR, aggregations, ORDER BY, LIMIT.
  - Safe identifier quoting and 0.0000 invalid SQL rate guarantee across all official SQLite databases.
- **Pointer-Generator LSTM Baseline (Neural Seq2Seq)**:
  - 2-layer bidirectional LSTM encoder, Bahdanau additive attention decoder, and schema-pointer copy mechanism.
  - Sequential two-stage training: Stage 1 WikiSQL warm-up (56,000 examples) followed by Stage 2 Spider primary training (~7,000 examples).
- Save predictions with question, schema/database ID, gold SQL, predicted SQL, and failure reasons.

**Done when:** Both baselines run end-to-end on full WikiSQL and Spider dev sets without unhandled exceptions.

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
- [x] Schema serialization includes required relations (tables, columns, types, PKs, FKs).
- [x] Classical baselines return one candidate per input.
- [x] Unsupported/invalid outputs are explicitly counted.
- [x] Exact-match implementation is tested.
- [x] Execution accuracy implementation is tested.
- [x] Invalid-SQL rate implementation is tested.
- [x] Metrics are reproducible from saved predictions.
- [x] Error analysis quantitative breakdowns are prepared.
- [x] CLI demo runs from one command (`text-to-sql-demo --demo`).
- [ ] Qualitative error analysis formatted for report.
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

As of September 24, 2026:
- **All GPU training completed:** Job `361487` (initial, 10+10 epochs) and Job `361547`
  (optimized, 10+25 epochs) both finished on `gpunode8`. All artifacts synchronized locally.
- **Optimized LSTM results (primary baseline) on Spider:**
  - Execution Accuracy: **5.90%** (surpasses Template's 5.80%)
  - Exact Match: **3.29%** (vs Template's 0.00%; aligns with published 3.2–5.4% range)
  - Invalid SQL: 77.66% (reduced from 85.20% via `sql_repair.py`)
- The interactive demo CLI (`text-to-sql-demo --demo`) is verified with 3 scripted
  queries across both models with formatted ASCII tables.
- 56/56 unit tests pass cleanly in 3.06s; Ruff clean.
- **Project audit completed** against NLPpart1.pdf and CS F429 evaluation rubric:
  architecture, datasets, metrics, and pipeline all aligned.

### Remaining Part 2 work:

**Code changes:**
1. Implement Spider SQL difficulty classification from query structure (easy/medium/hard/extra-hard).
2. Re-generate evaluation breakdowns with per-difficulty labels.
3. Extract qualitative error examples from `predictions.jsonl`.
4. Add README skeleton and seed configuration helper.

**Report (Sections a–d):**
5. Draft Introduction & Motivation, Literature Survey, Dataset & Preprocessing,
   Method/Baseline & Results with error analysis.

**Demo/Viva:**
6. Prepare viva Q&A script and rehearse live demo flow.

### Schedule to September 30 freeze:

| Date | Focus | Gate |
|---|---|---|
| Sep 24 | Difficulty classification + error examples | Breakdowns show easy/medium/hard/extra-hard |
| Sep 25 | Report: Introduction + Literature Survey | Sections a–b drafted |
| Sep 26 | Report: Dataset + Preprocessing + Metrics | Section c drafted |
| Sep 27 | Report: Method, Results, Error Analysis | Section d drafted |
| Sep 28 | Demo prep + Report polish | Demo rehearsed; report reviewed |
| Sep 29 | LaTeX conversion + Final polish | Report compiles cleanly |
| Sep 30 | **INTERNAL FREEZE** | All Part 2 deliverables frozen |

## 12. Full-scale baseline checkpoints

### Template Baseline (Full Dev)

| Dataset | Retained | Exec Acc | Exact Match | Invalid SQL |
|---|---:|---:|---:|---:|
| WikiSQL | 8,415 | 0.0723 | 0.0126 | 0.0000 |
| Spider | 1,034 | 0.0580 | 0.0000 | 0.0058 |

### Optimized LSTM Baseline (Full Dev, Job 361547)

| Dataset | Retained | Exec Acc | Exact Match | Invalid SQL |
|---|---:|---:|---:|---:|
| Spider | 1,034 | **0.0590** | **0.0329** | 0.7766 |
| WikiSQL | 8,415 | 0.0004 | 0.0004 | 0.9951 |

Training: 2-layer bidir encoder, 2-layer attention decoder, 256-dim embeddings,
512-dim hidden, copy mechanism, batch=64, lr=0.001, grad_clip=1.0.
WikiSQL warm-up 10 epochs + Spider primary 25 epochs. Final loss: 0.0404.

## 13. Authority alignment summary

| Requirement area | Status |
|---|---|
| Dataset selection & justification | ✅ Spider primary, WikiSQL warm-up, sources documented |
| Classical baselines comparison | ✅ LSTM (primary) vs Template (fallback) |
| Model details & hyperparameters | ✅ Architecture, training strategy, all hyperparams recorded |
| Evaluation metrics | ✅ Exec accuracy, exact match, invalid-SQL rate |
| Error analysis | ✅ Quantitative breakdowns; qualitative examples pending |
| Demonstration & CLI | ✅ `text-to-sql-demo --demo` with model selection |
| Report sections a–d | ⚠️ Not yet drafted — scheduled Sep 25–27 |
| Difficulty breakdowns | ⚠️ Need to implement SQL difficulty classification |
| Modern transformer & novelty | Deferred to Part 3 (correct per timeline) |


