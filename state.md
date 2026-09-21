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
- Initialized local Git on `spec/agent-governance-rules`.
- Configured the intended `origin` remote.
- Added agent governance rules for surgical edits, clarification, configuration,
  branch/PR safety, and progress tracking.

## Current roadblocks

- The GitHub repository was initially empty, so GitHub currently treats
  `spec/agent-governance-rules` as its default branch. A proper default branch
  and PR base should be established before merging feature work.
- Dataset acquisition, typed data contracts, and the implementation baseline are
  not set up yet.
- No model implementation or demo exists yet.
- HPC hostname, username, remote project path, and scheduler details are not
  confirmed.
- The modern-model dependency set is intentionally not installed yet; it will
  be added only after the Part 2 baseline and compute requirements are clearer.
- Evaluation policy decisions remain open: literal-sensitive exact-match
  diagnostic, result ordering, accuracy denominators, and Spider split policy.

## Next immediate steps

1. Confirm the repository default-branch strategy and PR base.
2. Add typed data contracts and synthetic SQLite fixtures on the feature branch.
3. Implement and test the WikiSQL data contract and schema serializer.
4. Implement the WikiSQL-first loader and deterministic schema serializer.
5. Confirm HPC connection details before creating a local SSH alias.

## Session metadata

| Field | Value |
|---|---|
| Last updated | 2026-09-21 |
| Active branch | `feature/part2-data-contracts` |
| Overall estimate | 22% |
| Next review point | After default-branch strategy and data contracts |
