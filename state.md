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
- Fixed an identifier-selection bug where “names of singers” selected
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

## Current roadblocks

- The GitHub repository was initially empty, so GitHub currently treats
  `spec/agent-governance-rules` as its default branch. A proper default branch
  and PR base should be established before merging feature work.
- The deterministic baseline remains limited on broader official data,
  especially Spider joins and compositional queries; the 250-example results
  are evidence, not final benchmark claims.
- Full-dev evaluation is currently running locally on CPU. HPC GPU submission
  remains paused due to partition configuration, and the deterministic
  SQLite-heavy evaluation is not GPU-accelerated.
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
- Scripted demos, full report-ready error analysis, and clean reproduction
  remain outstanding.
- HPC GPU job submission is currently paused; CPU-only work can continue.
  Connectivity is healthy, but scheduler resource details and GPU partition
  readiness must be confirmed before submitting jobs.
- PR creation is now approval-gated; no automatic PRs for ordinary checkpoints.
- No LSTM implementation, transformer model, or novelty implementation exists
  yet. The A1 design is approved and preprocessing is the next implementation
  checkpoint.
- HPC remote project path and scheduler details are not confirmed.
- The modern-model dependency set is intentionally not installed yet; it will
  be added only after the Part 2 baseline and compute requirements are clearer.
- Evaluation policy decisions remain open: literal-sensitive exact-match
  diagnostic, result ordering, accuracy denominators, and Spider split policy.

## Next immediate steps

1. Implement model-side tokenization and training-only vocabulary/copy-target
   handling for the additive LSTM.
2. Add vocabulary and copy-mechanism tests.
3. Add the bounded CPU smoke training loop and checkpoint reload test.
4. Run comparable LSTM WikiSQL/Spider smoke evaluations through the existing
   metrics and reports.
5. Inspect baseline breakdowns and select representative successes/failures.
6. Add scripted easy/filter/failure demo examples and rehearse the CLI.
7. Draft report sections and evidence required by Part 2.
8. Confirm the HPC remote project path and scheduler before any job workflow.
9. Continue CPU-only work while GPU submission is paused.
10. Do not open another PR until the user requests it or approves a notified
    major-checkpoint PR recommendation.

## Session metadata

| Field | Value |
|---|---|
| Last updated | 2026-09-21 |
| Active branch | `feature/part2-authority-review` |
| Overall estimate | 76% |
| Next review point | LSTM preprocessing checkpoint |
