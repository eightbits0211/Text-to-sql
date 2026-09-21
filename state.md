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
- Dataset acquisition and loaders are not set up yet.
- HPC GPU job submission is currently paused; CPU-only work can continue.
- PR creation is now approval-gated; no automatic PRs for ordinary checkpoints.
- No model implementation or demo exists yet.
- HPC remote project path and scheduler details are not confirmed.
- The modern-model dependency set is intentionally not installed yet; it will
  be added only after the Part 2 baseline and compute requirements are clearer.
- Evaluation policy decisions remain open: literal-sensitive exact-match
  diagnostic, result ordering, accuracy denominators, and Spider split policy.

## Next immediate steps

1. Review the WikiSQL loader checkpoint; PR creation is approval-gated.
2. Add Spider loader support and cross-domain fixture coverage.
3. Add deterministic dataset statistics and exclusion reporting for Spider.
4. Confirm the HPC remote project path and scheduler before creating a local
   project sync/job workflow.
6. Continue CPU-only fixtures, loaders, evaluator, and CLI work while GPU
   submission is paused.
7. Do not open another PR until the user requests it or approves a notified
   major-checkpoint PR recommendation.
6. Before the next session ends, update this file and provide a context-history
   summary.

## Session metadata

| Field | Value |
|---|---|
| Last updated | 2026-09-21 |
| Active branch | `feature/part2-wikisql-loader` |
| Overall estimate | 36% |
| Next review point | After WikiSQL loader review and Spider loader planning |
