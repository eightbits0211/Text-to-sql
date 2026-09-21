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
- Full test suite now passes with 18 tests and Ruff clean.
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
- WikiSQL smoke execution is still zero for the deterministic template
  baseline, so question parsing and condition rendering need improvement.
- Spider smoke execution is 0.4000; remaining failures are mostly projection,
  ordering, aggregation, and table/column selection limitations.
- HPC GPU job submission is currently paused; CPU-only work can continue.
- PR creation is now approval-gated; no automatic PRs for ordinary checkpoints.
- No modern model or novelty implementation exists yet.
- HPC remote project path and scheduler details are not confirmed.
- The modern-model dependency set is intentionally not installed yet; it will
  be added only after the Part 2 baseline and compute requirements are clearer.
- Evaluation policy decisions remain open: literal-sensitive exact-match
  diagnostic, result ordering, accuracy denominators, and Spider split policy.

## Next immediate steps

1. Review the baseline, evaluation-report, official-data smoke checkpoint;
   PR creation is approval-gated and no PR is currently open.
2. Inspect the saved official-data prediction/report artifacts and categorize
   WikiSQL failures.
3. Improve WikiSQL schema matching, condition extraction, and projection
   parsing with targeted tests.
4. Confirm the HPC remote project path and scheduler before creating a local
   project sync/job workflow.
5. Continue CPU-only work while GPU submission is paused.
6. Do not open another PR until the user requests it or approves a notified
   major-checkpoint PR recommendation.
7. Before the next session ends, update this file and provide a context-history
   summary.

## Session metadata

| Field | Value |
|---|---|
| Last updated | 2026-09-21 |
| Active branch | `feature/part2-classical-baseline` |
| Overall estimate | 70% |
| Next review point | After WikiSQL parser improvements and smoke rerun |
