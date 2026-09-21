# Text-to-SQL Project Progress Log

This is the authoritative high-level progress table. Every agent session must
update it after completing a checkpoint, discovering a blocker, or changing
scope. Percentages are estimates of completed **project checkpoints**, not
claims about final model accuracy.

## Current status

| Field | Value |
|---|---|
| Last updated | 2026-09-21 |
| Overall completion | 78% |
| Current phase | LSTM preprocessing completed |
| Part 2 internal freeze | 2026-09-30 |
| Official Part 2 deadline | 2026-10-15, 23:55 IST |
| Active branch | `feature/lstm-preprocessing` |
| Current blocker | HPC login works and Slurm is available, but GPU partition/readiness and remote project path remain unconfirmed; repository default-branch strategy also remains open |
| Next checkpoint | Implement bounded 200-example CPU smoke training loop and checkpoint reload test |

## Checkpoint log

| ID | Workstream | Checkpoint | Status | Completion | Owner | Evidence / notes | Next action |
|---|---|---|---|---:|---|---|---|
| P2.24 | LSTM baseline | Model-side tokenization, training-only vocabulary, and copy-target handling | Done | 100% | Lead agent | `src/text_to_sql/lstm/preprocessing.py`; 7 tests pass; Ruff clean | Implement CPU smoke training loop |
| P0.1 | Requirements | Course PDFs reviewed and scope extracted | Done | 100% | Lead agent | Text-to-SQL, Spider/WikiSQL, baseline/demo/report requirements recorded | Maintain traceability |
| P0.2 | Product | Main PRD created | Done | 100% | Lead agent | [`text-to-sql-prd.md`](./text-to-sql-prd.md) | Update only when scope changes |
| P0.3 | Part 2 | Part 2 plan and Sep 30 internal freeze created | Done | 100% | Lead agent | [`part-2-submission-plan.md`](./part-2-submission-plan.md) | Execute checkpoints |
| P0.4 | Governance | Agent rules created and updated | Done | 100% | Lead agent | [`agent-rules.md`](./agent-rules.md) | Apply to every agent |
| P0.5 | Git | Local Git initialized and origin configured | Done | 100% | Lead agent | Branch `spec/agent-governance-rules`; no commit/push yet | Create reviewed baseline commit |
| P1.1 | Repository | Review current files and choose tracked scope | In progress | 25% | Lead agent | PDFs and planning files currently present | Decide `.gitignore` and tracked docs |
| P1.2 | Architecture | System architecture documented | Done | 100% | Lead agent | [`system-architecture.md`](./system-architecture.md) | Validate against implementation |
| P1.3 | Planning | Granular checkpoint plan documented | Done | 100% | Lead agent | [`implementation-checkpoints.md`](./implementation-checkpoints.md) | Start P2 checkpoints |
| P1.4 | Coordination | Sub-agent operating model documented | Done | 100% | Lead agent | [`sub-agent-coordination-plan.md`](./sub-agent-coordination-plan.md) | Assign bounded tasks |
| P1.5 | State | Persistent session state file created | Done | 100% | Lead agent | [`../state.md`](../state.md) | Update at session end |
| P1.6 | Technology | Technology stack documented | Done | 100% | Lead agent | [`tech-stack.md`](./tech-stack.md) | Verify versions during setup |
| P1.7 | Authority | PRD audited against authoritative PDFs | Done | 100% | Lead agent | [`prd-authority-audit.md`](./prd-authority-audit.md) | Preserve traceability |
| P1.8 | Coordination | Environment and data-pipeline agents completed bounded reports | Done | 100% | Lead agent | Agent reports received; no files modified | Resolve setup decisions |
| P1.9 | Coordination | Evaluation-contract agent report | Done | 100% | Evaluation agent | Shared evaluator contracts and fixture acceptance checks received | Confirm policy decisions |
| P2.1 | Environment | Python 3.12 + uv environment and smoke test | Done | 100% | Lead agent | `uv sync --dev`, pytest, Ruff, and SQLite smoke test pass | Implement data contracts |
| P2.2 | Repository | Initial project baseline pushed | Done | 100% | Lead agent | Commits `72fbc48`, `cee1f4e`; branch pushed using `eightbits0211` CLI account | Establish PR base/default branch |
| P2.3 | HPC | HPC security/setup notes documented | Done | 100% | Lead agent | [`hpc-setup.md`](./hpc-setup.md); no key read or copied | Confirm host/user/scheduler |
| P2.4 | Governance | Session-end context-history rule documented | Done | 100% | Lead agent | [`agent-rules.md`](./agent-rules.md) and [`../state.md`](../state.md) updated | Apply at every session end |
| P2.5 | Data | Typed contracts and deterministic schema serializer | Done | 100% | Lead agent | `src/text_to_sql/data/`; 3 tests pass; Ruff passes; PR #2 merged | Add SQLite fixtures |
| P2.6 | HPC | Non-destructive SSH authentication test | Done | 100% | Lead agent | Host authentication succeeded; no key contents accessed | Confirm remote path/scheduler |
| P2.7 | Repository/HPC | PR #1 merged and GPU submission pause recorded | Done | 100% | Lead agent | PR #1 merged; HPC team pause is documented | Continue CPU-only work; resume GPU work when enabled |
| P2.8 | Data | SQLite schema extraction and synthetic fixture tests | Done | 100% | Lead agent | `sqlite_schema.py`; 6 tests pass; Ruff passes | Implement WikiSQL loader |
| P2.10 | Data | WikiSQL JSON loader and exclusion statistics | Done | 100% | Lead agent | `wikisql.py`; 9 tests pass; Ruff passes; no PR opened yet | Implement Spider loader |
| P2.11 | Data/Evaluation | Spider loader, fixtures, and CPU evaluation harness | Done | 100% | Lead agent | `spider.py`, `metrics.py`; 12 tests pass; Ruff passes; no PR opened | Review checkpoint and select baseline |
| P2.12 | Baseline | Deterministic template baseline and shared prediction adapter | Done | 100% | Lead agent | `baselines/template.py`; count/aggregate generation and evaluation adapter covered by tests | Evaluate against downloaded benchmark data |
| P2.13 | Artifacts | JSONL prediction artifact persistence | Done | 100% | Lead agent | `evaluation/artifacts.py`; one-record-per-example fixture test | Add persisted metric reports |
| P2.14 | Demo | CLI question → SQL → read-only result | Done | 100% | Lead agent | `text-to-sql-demo` entry point and `cli.py` | Add documented smoke command |
| P2.15 | Evaluation | Difficulty, query-structure, error breakdowns and report files | Done | 100% | Lead agent | `evaluation/reports.py`; JSON, CSV, and Markdown fixture outputs; 14 tests pass | Run on real benchmark predictions |
| P2.16 | Reproducibility | Typed dataset configuration and smoke runner | Done | 100% | Lead agent | `config.py`, `data/README.md`, `scripts/run_part2_smoke.py`; explicit missing-path failure and CLI help | Configure real dataset paths |
| P2.17 | Dataset/Evaluation | Official WikiSQL and Spider download and smoke run | Done | 100% | Lead agent | External archives verified; 5 retained/0 excluded per dataset; artifacts written outside Git; Spider execution accuracy 0.4000, WikiSQL 0.0000 | Improve WikiSQL parsing |
| P2.18 | Evaluation | Result-table comparison policy | Done | 100% | Lead agent | Execution comparison now ignores SQL result-column label case; row order remains sensitive; regression test added; 18 tests pass | Reassess ordering policy before full evaluation |
| P2.19 | Review | Part 2 merge and authority alignment review | Done | 100% | Lead agent | PR #5 merged as `048cae6`; current implementation aligned with Part 2 PDF requirements, with report/evidence gaps recorded | Improve baseline and prepare report |
| P2.20 | Baseline | Projection, condition, aggregation, and multi-condition parsing | Done | 100% | Classical baseline agent | 22 tests pass; official 25-example smoke results: WikiSQL 0.0800, Spider 0.0800 execution accuracy | Run larger evaluation and analyze errors |
| P2.21 | Baseline | Identifier-aware projection selection | Done | 100% | Lead agent | Regression test confirms “names of singers” selects `Name`, not `Singer_ID`; 23 tests pass; CLI verified | Run larger evaluation and analyze errors |
| P2.22 | Baseline/Debugging | User-reported names projection bug fixed | Done | 100% | Lead agent | Reproduced CLI output selecting `Singer_ID`; updated semantic column scoring; 23 tests pass; CLI now prints six singer names | Run larger evaluation and analyze errors |
| P2.23 | LSTM baseline | Additive LSTM architecture and copy-mechanism design | **Checkpoint — awaiting user review** | 100% | Lead agent | [`lstm-baseline-design.md`](./lstm-baseline-design.md); specifies encoder, attention decoder, training-only vocabulary, schema-identifier copy mechanism, CPU/Colab configurations, and shared evaluation boundaries; no implementation code added | Review design, then proceed to A2/A3 tokenization and vocabulary |
| P2.9 | Governance | PR creation made approval-gated | Done | 100% | Lead agent | [`agent-rules.md`](./agent-rules.md) updated; no automatic PR policy | Notify user at major checkpoints |
| P2.1 | Environment | Dependency manifest and smoke-test command | Not started | 0% | Unassigned | Required before data/model work | Inspect available Python environment |
| P2.2 | Data | Dataset configuration and acquisition instructions | Not started | 0% | Unassigned | WikiSQL first, Spider second | Define config and paths |
| P2.3 | Data | WikiSQL loader and validation | Not started | 0% | Unassigned | Part 2 gate | Implement fixtures/tests |
| P2.4 | Data | Schema serialization | Not started | 0% | Unassigned | Tables, columns, types, keys | Implement deterministic serializer |
| P2.5 | Data | Spider loader and smoke split | Not started | 0% | Unassigned | Preserve official split metadata | Implement after WikiSQL |
| P2.6 | Baseline | Classical parser/template baseline | Done | 100% | Lead agent | Deterministic schema-aware template baseline implemented | Evaluate against downloaded benchmark data |
| P2.7 | Evaluation | Exact match, execution accuracy, invalid rate | Not started | 0% | Unassigned | Per-example failures must continue | Build fixture-driven evaluator |
| P2.8 | Analysis | Error categories and breakdown reports | Not started | 0% | Unassigned | Difficulty and query structure required | Generate CSV/Markdown reports |
| P2.9 | Demo | CLI question → SQL → result/error | Done | 100% | Lead agent | CLI integrated with read-only SQLite execution | Add documented smoke command |
| P2.10 | Report | Part 2 report sections and citations | Not started | 0% | Unassigned | Introduction through baseline results | Draft from saved evidence |
| P2.11 | QA | Clean-environment reproduction and PR review | Not started | 0% | Unassigned | Required before Sep 30 freeze | Run final checklist |

## Update protocol

When changing this log:

1. Update `Last updated`, `Overall completion`, and `Next checkpoint`.
2. Change only affected rows; preserve historical notes. Do not update this
   file for every small edit, test, or intermediate command.
3. Set status to one of `Not started`, `In progress`, `Blocked`, `Done`, or
   `Deferred`.
4. Add evidence such as a file, test command, metric artifact, or PR link.
5. Record blockers explicitly instead of lowering the percentage silently.

## Decision and evidence record

### 2026-09-21 — Classical baseline selection

- **Decision:** Use the deterministic template/grammar parser as the Part 2
  classical baseline.
- **Alternatives considered:** Sequence-to-sequence LSTM.
- **Reason:** Both are allowed by the project requirements. The template
  parser remains the CPU-friendly, deterministic primary baseline, while the
  LSTM is now an additive secondary baseline with a CPU fallback and Colab
  path. HPC GPU submission remains paused.
- **Impact:** Part 2 now includes a bounded LSTM comparison without removing,
  changing, or blocking the existing template deliverable.
- **Future compatibility:** Both baselines use the shared fit/predict/evaluate
  contract and can use the same evaluator and CLI.

### 2026-09-21 — LSTM architecture checkpoint A1

- **Decision:** Add an attention-based bidirectional LSTM seq2seq model with a
  pointer-generator copy mechanism for unseen schema identifiers.
- **Design:** Embedding dimension 256, hidden dimension 512, packed sequences,
  training-only vocabulary, greedy decoding first, and CPU/Colab configurations
  are documented in [`lstm-baseline-design.md`](./lstm-baseline-design.md).
- **Integration constraint:** Existing loaders, typed records, metrics,
  reports, artifacts, CLI, and template baseline remain unchanged.
- **Status:** **Checkpoint awaiting user review.** No model code or dependency
  changes have been made.
- **Next action:** After approval, implement A2/A3 model-side tokenization,
  training-only vocabulary construction, and copy-target tests.

### 2026-09-21 — Official smoke and projection correction

- **Initial observation:** On the official 25-example slices, execution
  accuracy was 0.0800 for WikiSQL and Spider.
- **User-reported bug:** “What are the names of all singers?” generated
  `SELECT "Singer_ID" FROM "singer"`.
- **Correction:** Added semantic name-column scoring and a regression test;
  the same CLI query now generates `SELECT "Name" FROM "singer"` and returns
  six names.
- **Evidence:** `uv run pytest` → 23 passed; Ruff passed; CLI smoke command
  verified manually.
- **Next action:** Run a larger evaluation and preserve a run manifest.

### 2026-09-21 — Template baseline design hardening

- **Decision:** The deterministic template parser is documented as a bounded,
  legitimate classical baseline, not as a complete SQL parser.
- **Scope recorded:** Single-table projections, counts, basic aggregations,
  comparison predicates, and `AND` conditions are supported. Joins,
  subqueries, set operations, grouping, ordering, limits, and `OR`
  predicates remain explicit limitations.
- **Implementation:** Added immutable capability declarations to
  `TemplateBaseline` and created [`template-baseline-design.md`](./template-baseline-design.md)
  with the input/output contract, grammar, determinism, and evaluation policy.
- **Regression evidence:** Added a capability-contract test; `uv run pytest
  tests/test_baseline_and_artifacts.py` → 9 passed; Ruff clean.
- **Next action:** Run a larger official template evaluation, preserve a
  manifest, and select representative successes/failures for the report.

### 2026-09-21 — Larger template evaluation and manifest

- **Run:** Evaluated the template baseline on the first 250 official
  development examples from WikiSQL and Spider using the existing loaders and
  evaluator.
- **Results:** WikiSQL retained 250/250, execution accuracy **0.1560**, exact
  match **0.1040**, invalid-SQL rate **0.0000**. Spider retained 250/250,
  execution accuracy **0.0720**, exact match **0.0000**, invalid-SQL rate
  **0.0000**.
- **Breakdown:** WikiSQL had 39 successful executions and 211 wrong-result
  cases. Spider had 18 successful executions and 232 wrong-result cases;
  Spider execution accuracy was 0.136 single-table and 0.029 join queries.
- **Interpretation:** The parser is syntactically robust on this slice but
  semantically limited, especially on Spider joins and compositional queries.
  These results support adding the LSTM rather than replacing the template
  baseline.
- **Reproducibility:** Added manifest generation to
  `scripts/run_part2_smoke.py`. Manifest records command, UTC timestamp,
  configuration, source SHA-256 hashes, Git commit, counts, metrics, and
  artifact directories. Saved outside Git at
  `/Users/roshini/datasets/text-to-sql/artifacts-template-250/run-manifest.json`.
- **Validation:** `uv run pytest` → 24 passed; Ruff clean.
- **Next action:** Implement model-side tokenization and training-only
  vocabulary construction for the additive LSTM.

### 2026-09-21 — Template efficiency improvements

- **Goal:** Improve the deterministic baseline before beginning LSTM work,
  using the 250-example error evidence while preserving the shared interfaces.
- **Changes:** Added multi-column projections, `DISTINCT`, multiple aggregate
  expressions, `ORDER BY`/top-N handling, question-order preservation,
  comparison aliases, implicit WikiSQL value links, and safer `OR` handling.
- **Regression correction:** A column-specific count heuristic improved some
  WikiSQL cases but reduced valid Spider count-query matches. It was removed,
  retaining the established `COUNT(*)` behavior.
- **Final results:** On the same 250-example slices, WikiSQL execution
  accuracy is **0.1560** and Spider is **0.0920**, both with invalid-SQL rate
  **0.0000**. Spider improved from the prior **0.0720**.
- **Validation:** `uv run pytest` → 29 passed; Ruff clean. Final artifacts and
  manifest are outside Git at
  `/Users/roshini/datasets/text-to-sql/artifacts-template-250-final2/`.
- **Decision:** Template efficiency work is complete for now. Further
  capability expansion should wait until the LSTM comparison, to avoid
  turning the classical baseline into an uncontrolled parser project.
- **Next action:** Begin LSTM model-side tokenization and training-only
  vocabulary/copy-target handling.

### 2026-09-21 — Full-dev evaluation started

- **Methodology decision:** The first-250 rows are not treated as an unbiased
  sample because both official dev files are grouped: WikiSQL begins with
  repeated table IDs, while Spider's first 250 records cover only four
  databases. The 250 results remain a fixed regression subset only.
- **Run started:** Full development evaluation launched with `--full-dev`:
  8,421 WikiSQL examples and 1,034 Spider examples, using the same prediction,
  evaluator, and report-generation path.
- **Expected runtime:** This is CPU/local execution, not HPC. HPC GPU
  submission remains paused due to partition configuration, and this
  deterministic template evaluation is not GPU-accelerated. The full run is
  slower than expected because each example executes gold and predicted SQL
  against SQLite with separate read-only database connections.
- **Artifact policy:** The run will write full predictions, `evaluation.json`,
  `breakdowns.csv`, `evaluation.md`, and a run manifest under
  `/Users/roshini/datasets/text-to-sql/artifacts-template-full-dev/`.
- **Next action:** Wait for completion, verify both dataset counts and all
  full-run breakdowns, then record the final report-ready metrics.

### 2026-09-21 — Full official dev evaluation complete

- **Coverage:** Full WikiSQL dev: 8,421 source records, 8,415 retained, 6
  excluded. Full Spider dev: 1,034 source records, 1,034 retained, 0
  excluded. This replaces the first-250 run as the report's headline
  evaluation.
- **WikiSQL results:** Execution accuracy **0.0723** (608/8,415), exact match
  **0.0126** (106/8,415), invalid-SQL rate **0.0000**. All retained records
  are single-table by construction.
- **Spider results:** Execution accuracy **0.0580** (60/1,034), exact match
  **0.0000**, invalid-SQL rate **0.0058** (6/1,034). Single-table execution
  accuracy was **0.1029** (56/544); multi-table join accuracy was **0.0091**
  (4/438); other structures were 0/52.
- **Breakdowns:** The same full-run records generated `evaluation.json`,
  `breakdowns.csv`, and `evaluation.md` for each dataset. Failure categories
  were regenerated from the full run: WikiSQL 608 successes/7,807 wrong
  results; Spider 60 successes/968 wrong results/6 invalid SQL.
- **Reproducibility:** Full artifacts and manifest are outside Git at
  `/Users/roshini/datasets/text-to-sql/artifacts-template-full-dev/`.
  Manifest records `smoke_limit: null`, source hashes, commit, timestamp,
  counts, and metrics.
- **Interpretation:** The 250-example metrics were not representative and are
  retained only as fast regression evidence. The full-dev results are the
  report-ready template baseline numbers, with explicit dataset coverage.
- **Validation:** Full-dev runner completed successfully; the 29-test suite
  and Ruff remain clean.
- **Next action:** Begin LSTM tokenization and training-only vocabulary work.

### 2026-09-21 — HPC connectivity check

- **Authentication:** Non-destructive SSH test succeeded using the existing
  local key path; the private key was not read, copied, or logged.
- **Remote identity:** The remote host reported `hpc01.sharanga.local`, user
  `csisnlp_20`, and home `/home/csisnlp_20`.
- **Scheduler:** Slurm is installed and reports version 25.05.3.
- **GPU visibility:** `nvidia-smi` is unavailable on the login node. This does
  not prove that compute-node GPUs are unavailable; a scheduled allocation or
  confirmed partition is required.
- **Environment:** `/usr/bin/python3` is available; `uv` is not currently on
  the login-node PATH.
- **Decision:** HPC is reachable and scheduler-backed, but not yet ready for
  an LSTM GPU run until the team confirms a GPU partition and job resource
  format. Continue local CPU preprocessing and smoke work.
- **Next action:** Confirm Slurm GPU partition name/resource syntax and remote
  project/dataset paths before submitting any job.

### 2026-09-21 — LSTM copy-mechanism design audit

- **Concern reviewed:** The pointer-generator is the riskiest LSTM subsystem
  because it combines attention, generation/copy mixing, extended-vocabulary
  target mapping, and exact identifier reconstruction.
- **Design revision:** Expanded [`lstm-baseline-design.md`](./lstm-baseline-design.md)
  with the per-example extended vocabulary, source-position mapping, duplicate
  token accumulation, padding mask, generation probability, mixed
  distribution, target precedence rules, teacher-forced NLL, decoding behavior,
  and explicit failure events.
- **Implementation boundary:** Copy support is now divided into seven testable
  units before full training: extended vocabulary, duplicate attention,
  fixed-vocabulary precedence, unseen identifier round-trip, unresolvable
  targets, normalized mixed distribution, and greedy reconstruction.
- **Fallback decision:** If copy support cannot pass its isolated tests before
  the CPU smoke gate, the LSTM will remain a restricted secondary experiment
  with the limitation reported explicitly; silent identifier guessing is not
  allowed, and the template remains primary.
- **Status:** A1 design is now materially specified; no LSTM code has been
  written yet.
- **Next action:** Implement the model-side tokenizer and copy-target data
  structures first, with focused unit tests before encoder/decoder training.

### 2026-09-21 — LSTM preprocessing checkpoint started

- **Branch:** Created `feature/lstm-preprocessing` after PR #6 merged and
  stale merged branches were removed locally and remotely.
- **Scope:** Implement only model-side tokenization, training-only vocabulary,
  and copy-target data structures. No encoder/decoder or training loop is
  included in this checkpoint.
- **Preservation gate:** Existing template behavior, loaders, evaluator,
  metrics, reports, artifacts, and public interfaces must remain unchanged.
- **Required tests:** Deterministic question/schema/SQL tokenization,
  training-only vocabulary isolation, unseen schema identifier copy targets,
  fixed-vocabulary precedence, duplicate source mapping, and explicit
  unresolvable-target events.
- **Next action:** Complete the preprocessing implementation and run the
  focused/full test suites before starting the packed encoder/attention
  decoder checkpoint.

### 2026-09-21 — Architecture and subagent documentation synchronized

- **Technology stack:** Corrected the runtime to Python 3.12 with `uv`,
  recorded PyTorch as the planned LSTM dependency, and documented CPU fallback,
  Colab fallback, and the verified-but-not-yet-GPU-ready Slurm HPC status.
- **System architecture:** Added explicit LSTM preprocessing/training
  boundaries for tokenization, training-only vocabulary, copy targets,
  checkpoint metadata, and shared evaluator integration. The template remains
  the primary baseline and the LSTM remains additive.
- **Subagent coordination:** Added a dedicated LSTM preprocessing/training role
  with boundaries preventing changes to loaders, template behavior, or the
  evaluator. Copy behavior must pass isolated tests before training work.
- **Evidence of subagent use:** The bounded LSTM preprocessing task was executed
  under agent ID `12a33cad-fdcf-4de4-be80-a01eb9ac573e`; prior bounded agents
  completed the template efficiency and baseline-quality tasks.
- **Next action:** Review the active preprocessing agent's implementation and
  integrate only after tests and Ruff pass.

### 2026-09-21 — LSTM preprocessing completed and verified

- **What changed:** Fixed keyword and case-normalization mismatch in
  `FixedVocabulary.get_index`, `FixedVocabulary.__contains__`, `build_copy_target`,
  and `resolve_target_token`. Added round-trip copy reconstruction assertion and
  duplicate unseen source token test in `tests/test_lstm_preprocessing.py`. Sorted
  `__all__` to satisfy Ruff.
- **Evidence:** 7 targeted unit tests in `tests/test_lstm_preprocessing.py` pass;
  Ruff passes cleanly across the repository.
- **Next action:** Proceed to the bounded 200-example CPU smoke training loop and
  checkpoint reload test.
