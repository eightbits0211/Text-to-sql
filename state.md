# Project State

This file is the persistent end-of-session handoff. The agent must update it
before ending every work session.

## What was completed

- Created the project PRD.
- Created the Part 2 submission plan with the September 30 internal freeze.
- Created the system architecture document.
- Created the granular implementation checkpoint plan.
- Created the sub-agent coordination plan.
- Created the technology stack document.
- Created the project progress log.
- Audited the PRD against both authoritative PDFs and corrected the Spider
  evaluation wording for hidden test labels.
- Launched and received reports from the environment and data-pipeline
  sub-agents.
- Confirmed the data-pipeline design: typed records, explicit exclusion events,
  deterministic schema serialization, official split preservation, and synthetic
  fixtures.
- Received the evaluation-contract report: separate exact match, execution
  accuracy, invalid-SQL rate, per-example records, safe SQLite execution,
  deterministic breakdowns, and fixture-driven tests.
- Selected and configured Python 3.12 with `uv`, `pyproject.toml`, and `uv.lock`.
- Added the initial `.gitignore`, package skeleton, and environment smoke test.
- Installed only the initial development tools: pytest and Ruff.
- Verified the environment smoke test, pytest, and Ruff all pass.
- Prepared the initial project documentation and setup for publication on the
  dedicated specification branch.
- Created local commit `72fbc48`
  (`chore: establish Text-to-SQL project baseline`).
- Pushed the baseline commits successfully after switching GitHub CLI
  authentication to `eightbits0211` and running `gh auth setup-git`.
- Created the next branch `feature/part2-data-contracts`; further work will not
  be committed to the temporary remote default branch.
- Documented HPC security and setup requirements without reading or copying the
  local private key.
- Recorded the supplied HPC host, username, and key path; non-destructive SSH
  authentication succeeded.
- Implemented the first data-contract slice:
  - typed dataset/enumeration contracts,
  - deterministic schema serialization,
  - required-field validation,
  - contract tests.
- Implemented read-only SQLite schema extraction and synthetic fixture tests for
  tables, columns, types, primary keys, and foreign keys.
- Implemented the WikiSQL JSON loader with structured SQL reconstruction,
  configurable database resolution, single-table filtering, schema attachment,
  and explicit exclusion/statistics reporting.
- Implemented the Spider loader with official-style schema metadata, database
  resolution, difficulty labels, query-structure classification, and exclusion
  statistics.
- Added Spider cross-domain join fixtures.
- Implemented the CPU-only evaluation harness for SQL normalization, read-only
  SQLite execution, exact match, execution accuracy, invalid-SQL rate, and
  per-example failure records.
- Implemented the deterministic, schema-aware template baseline with a shared
  fit/predict/evaluate adapter.
- Added JSONL prediction artifact persistence with example, gold, prediction,
  and model metadata.
- Added the `text-to-sql-demo` CLI for database selection, schema inspection,
  question-to-SQL generation, validation, and result output.
- Added deterministic evaluation report generation with difficulty,
  query-structure, and failure-category breakdowns in JSON, CSV, and Markdown.
- Added typed Part 2 configuration with environment-variable path overrides,
  artifact-directory resolution, and explicit missing-path validation.
- Added dataset acquisition/layout instructions and a bounded WikiSQL/Spider
  smoke runner that writes prediction and evaluation artifacts.
- Downloaded and extracted the official WikiSQL and Yale Spider releases
  outside the repository; recorded source URLs and archive SHA-256 hashes in
  `/Users/roshini/datasets/text-to-sql/dataset-manifest.json`.
- Ran the bounded official-data smoke evaluation with 5 WikiSQL and 5 Spider
  development examples; both retained 5 examples with 0 exclusions. The
  template baseline achieved 0.0000 WikiSQL and 0.4000 Spider execution
  accuracy.
- Updated execution comparison to ignore SQL result-column label case while
  retaining order-sensitive row comparison, with a regression test.
- Raised and merged PR #5 for the official-dataset smoke checkpoint:
  `https://github.com/eightbits0211/Text-to-sql/pull/5`.
- Audited the implementation against the authoritative project description and
  evaluation PDF. The Part 2 baseline stage is aligned, while report evidence,
  larger evaluation, scripted demos, and baseline quality remain outstanding.
- Delegated the bounded baseline-quality task to the classical baseline
  subagent. It added projection, comparison/equality condition, multi-condition,
  aggregation, and limited age/country parsing with targeted tests.
- Revalidated the official data with a 25-example slice per dataset: 25
  retained and 0 excluded for each; execution accuracy improved to 0.0800 for
  both WikiSQL and Spider.
- Fixed an identifier-selection bug where "names of singers" selected
  `Singer_ID`; the baseline now selects `Name`. Added a regression test and
  verified the CLI returns all six singer names.
- Formalized the template baseline contract and supported/unsupported grammar
  in [`docs/template-baseline-design.md`](docs/template-baseline-design.md).
- Added template capability declarations and regression coverage.
- Ran a 250-example-per-dataset official development evaluation:
  WikiSQL execution accuracy 0.1560 and Spider execution accuracy 0.0720,
  both with invalid-SQL rate 0.0000.
- Added reproducible run-manifest generation to
  `scripts/run_part2_smoke.py`; artifacts are stored outside Git under
  `/Users/roshini/datasets/text-to-sql/artifacts-template-250/`.
- Improved the template baseline with multi-column projections, `DISTINCT`,
  multiple aggregates, ordering/limits, question-order preservation, common
  aliases, and safer unsupported `OR` handling.
- Re-ran the same 250-example slices after correcting a count heuristic:
  WikiSQL execution accuracy is 0.1560 and Spider is 0.0920, improving the
  prior Spider result of 0.0720 without changing evaluation interfaces.
- Full validation now passes 29 tests with Ruff clean.
- Confirmed that the first-250 dev rows are grouped rather than demonstrably
  shuffled: WikiSQL's first 250 cover 62 tables and Spider's first 250 cover
  only four databases. Full-dev evaluation was therefore approved and started
  with the new `--full-dev` runner option.
- Clarified the modeling decision in the technology stack: the deterministic
  template/grammar parser is the selected Part 2 classical baseline; an LSTM
  is now approved as an additive secondary baseline, not a replacement.
- Completed LSTM Phase A1 design checkpoint in
  [`docs/lstm-baseline-design.md`](docs/lstm-baseline-design.md). The design
  specifies a bidirectional packed-sequence encoder, attention decoder,
  training-only vocabulary, pointer-generator copy mechanism for unseen schema
  identifiers, CPU smoke training, Colab-ready configuration, and unchanged
  shared evaluation interfaces.
- Clarified that Hugging Face Transformers is reserved for the planned Part 3
  modern model and has not yet been installed or trained.
- Updated the progress-log rule to record every meaningful checkpoint, decision,
  bug fix, experiment, blocker, and handoff with evidence and next action.
- Full test suite now passes with 23 tests and Ruff clean.
- Opened PR #3 for the SQLite schema/fixture slice:
  `https://github.com/eightbits0211/Text-to-sql/pull/3`.
- Updated governance so PRs are raised only when explicitly requested or after
  notifying the user that a major checkpoint is ready and receiving approval.
- Merged PR #1 into `spec/agent-governance-rules`.
- Merged PR #2 for the data-contract slice:
  `https://github.com/eightbits0211/Text-to-sql/pull/2`.
- Merged PR #1 successfully and synchronized the local base branch.
- Recorded the HPC team's notice that GPU job submission is paused while GPU
  partitioning configuration is completed.
- Added a standing rule to provide a context-history summary before every
  session ends.
- Initialized local Git on `spec/agent-governance-rules`.
- Configured the intended `origin` remote.
- Added agent governance rules for surgical edits, clarification, configuration,
  branch/PR safety, and progress tracking.
- Full-dev evaluation completed: WikiSQL retained 8,415/8,421 with execution
  accuracy 0.0723; Spider retained 1,034/1,034 with execution accuracy
  0.0580. Full breakdowns and manifest are under
  `/Users/roshini/datasets/text-to-sql/artifacts-template-full-dev/`.
- Rechecked HPC connectivity non-destructively. SSH succeeded; remote host is
  `hpc01.sharanga.local`, user is `csisnlp_20`, home is
  `/home/csisnlp_20`. Slurm 25.05.3 is available. `nvidia-smi` is not
  available on the login node, and `uv` is not on its PATH. GPU partition,
  compute-node visibility, and remote project paths remain unconfirmed.
- Audited and substantially expanded the LSTM pointer-generator specification.
  The design now defines the per-example extended vocabulary, generation/copy
  mixture equation, target mapping precedence, teacher-forced NLL, padding
  masks, duplicate-source accumulation, exact copied-token reconstruction,
  explicit unknown-token failures, and isolated copy-mechanism test gates.
- Implemented and verified LSTM preprocessing on `feature/lstm-preprocessing`:
  deterministic tokenization, training-only vocabulary, copy-target structures
  with pointer-generator extended vocabulary, resolution precedence, and
  unresolvable target events. 7 unit tests pass and Ruff is clean.
- Addressed LSTM preprocessing nuances: updated `_normalize_token` to strip
  enclosing quotes during matching, added `encoder_tokens` to `TokenizedExample`
  with `<bos>`, `<schema_sep>`, `<eos>`, added `encoder_positions` to `CopyTarget`
  to directly align encoder attention weights, cached tokenization in vocabulary
  construction, and added 2 regression unit tests. All 38 tests pass with Ruff clean.
- Implemented the LSTM smoke training loop on `feature/lstm-preprocessing`:
  installed torch 2.14.0 (CPU), created `model.py` (bidir encoder + attention
  decoder + pointer-generator), `collation.py` (padded tensor batches),
  `training.py` (teacher-forced NLL, Adam, grad-clip, checkpoint save/reload),
  and `adapter.py` (fit/predict/evaluate, mirrors TemplateBaseline interface).
  All 43 tests pass with Ruff clean.
- Synchronized the technology stack, system architecture, and subagent
  coordination documents with the approved additive LSTM workflow. The stack
  now records Python 3.12/`uv`, PyTorch for LSTM work, CPU/Colab fallback, and
  verified Slurm connectivity without claiming GPU readiness.
- Created `scripts/run_lstm_comparison.py` and completed the 200-example
  comparative evaluation between `TemplateBaseline` and `LSTMBaseline` on official
  WikiSQL and Spider development slices through the shared evaluation harness.
- Formatted detailed evaluation report artifact `lstm_comparison_report.md` with
  execution accuracy, exact match, invalid SQL rates, and failure diagnostics.
- Verified GPU readiness: the model architecture, batch collation, and training
  pipeline are fully device-agnostic (`torch.device`) and ready for CUDA/Colab/HPC.
- Added file patterns to `.gitignore` to prevent accidental tracking of PDFs,
  LaTeX logs, and editor caches.
- Merged Pull Request #7 into `spec/agent-governance-rules` without conflicts.
- Enhanced `src/text_to_sql/cli.py` to support the live demo showcase (Phase 8.7 & 8.14):
  implemented `--demo` flag running the three required showcase queries (easy projection,
  numeric comparison filter, and graceful failure handling) with model selection
  (`--model template|lstm`) and formatted ASCII tables.
- Created `tests/test_cli.py` with 6 unit tests covering parser configuration, table formatting,
  query execution, and CLI exit codes. All 49 unit tests pass cleanly in 2.94s.
- GPU verification job `359139` completed successfully on `gpunode8`: NVIDIA RTX PRO 6000
  Blackwell Server Edition (98 GB VRAM, CUDA 13.0, sm_120), PyTorch 2.14.0+cu130 tensor
  allocation and matrix multiplication verified under MPS 50% slice (47 GB pinned VRAM).
- **2026-09-22: LSTM designated as primary baseline** per user direction.
- Conducted comprehensive preprocessing audit: reviewed all files in `data/`,
  `lstm/preprocessing.py`, `lstm/collation.py`, `lstm/training.py`, `lstm/adapter.py`,
  `lstm/model.py`, and `evaluation/metrics.py`. Identified 8 issues (3 critical,
  3 medium, 2 low).
- Applied critical fixes:
  1. Added epoch shuffling with deterministic per-epoch seeded RNG (`training.py`).
  2. Added missing `--device` and `--batch-size` argparse arguments (`run_lstm_comparison.py`).
  3. Wired `args.batch_size` and `args.device` into the comparison manifest.
- Applied medium fixes:
  4. Eliminated redundant re-tokenization in batch collation (`collation.py`).
  5. Fixed `CopyTarget.encoder_positions` type annotation default (`preprocessing.py`).
  6. Added warning when `build_training_vocabulary` receives no TRAIN records.
- Applied low fixes:
  7. Properly imported `CopyTarget` in `adapter.py` (removed `# noqa: F821`).
  8. Fixed `forward_step` return type annotation in `model.py`.
- Identified and resolved a severe data loading bottleneck in WikiSQL and Spider:
  cached read-only SQLite schema introspection via `@lru_cache` and verified database
  paths once per file, reducing 56k WikiSQL dataset loading from ~15 hours to ~12 seconds.
- Added periodic batch progress reporting (every 200 batches) and unbuffered stdout
  logging (`PYTHONUNBUFFERED=1`, `python3 -u`) in `training.py` and `hpc_run_lstm_gpu.sh`.
- Resubmitted full two-stage GPU training job on Slurm: **Job `359924`** (`csis_gpu_lstm` on `gpunode8`).
- All 50 tests pass in 3.33s; Ruff clean. Commit `28bd307` pushed to origin.

## Current roadblocks

- GPU training job `359924` is queued on `gpunode8` (reason: Resources).
  It will auto-start as soon as a GPU MPS slice opens up.
- Part 2 report drafting (Introduction, Literature Survey, Dataset &
  Preprocessing, Methodology & Baseline Results with Error Analysis) remains
  to be authored. This is the **critical path** item.
- Evaluation policy decisions remain open: literal-sensitive exact-match
  diagnostic, result ordering, accuracy denominators, and Spider split policy.

## Next immediate steps

1. Monitor GPU training job `359924` until completion; retrieve checkpoints and
   run full comparative evaluation (`--full-eval`).
2. Draft Part 2 report sections (Sections a–d) incorporating dataset
   statistics, dual-baseline architecture (LSTM primary, template comparison),
   comparative results tables, and error analysis.
3. Prepare error analysis tables with representative examples for the report.
4. Review and raise PR for the bug fixes and report draft.

## Session metadata

| Field | Value |
|---|---|
| Last updated | 2026-09-23 |
| Active branch | `spec/agent-governance-rules` |
| Primary baseline | Pointer-Generator LSTM Seq2Seq |
| Fallback baseline | Deterministic Template Parser |
| Overall estimate | 85% |
| HPC Job ID | `359924` (`csis_gpu_lstm` on `gpunode8`) |
| Test suite status | 50 passed, 0 failed, Ruff clean |
| Next review point | GPU results retrieval and Part 2 report drafting |
