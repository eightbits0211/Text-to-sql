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
- Installed initial development tools: pytest and Ruff.
- Verified the environment smoke test, pytest, and Ruff all pass.
- Prepared initial project documentation and setup on dedicated specification branch.
- Created local commit `72fbc48` (`chore: establish Text-to-SQL project baseline`).
- Pushed baseline commits after switching GitHub CLI authentication to `eightbits0211` and running `gh auth setup-git`.
- Implemented first data-contract slice:
  - typed dataset/enumeration contracts,
  - deterministic schema serialization,
  - required-field validation,
  - contract tests.
- Implemented read-only SQLite schema extraction and synthetic fixture tests for
  tables, columns, types, primary keys, and foreign keys.
- Implemented WikiSQL JSON loader with structured SQL reconstruction,
  configurable database resolution, single-table filtering, schema attachment,
  and explicit exclusion/statistics reporting.
- Implemented Spider loader with official-style schema metadata, database
  resolution, difficulty labels, query-structure classification, and exclusion
  statistics.
- Added Spider cross-domain join fixtures.
- Implemented CPU evaluation harness for SQL normalization, read-only
  SQLite execution, exact match, execution accuracy, invalid-SQL rate, and
  per-example failure records.
- Implemented deterministic, schema-aware template baseline with shared
  fit/predict/evaluate adapter.
- Hardened deterministic template baseline and evaluated across full official
  development splits: 8,415 WikiSQL records (0.0768 exec acc) and 1,034 Spider
  records (0.1364 exec acc) with 0.0000 invalid SQL rate.
- Audited and expanded LSTM pointer-generator specification:
  extended vocabulary, generation/copy mixture equation, target mapping
  precedence, teacher-forced NLL, padding masks, duplicate-source accumulation,
  exact copied-token reconstruction, and explicit unknown-token failures.
- Implemented and verified LSTM preprocessing: deterministic tokenization,
  training-only vocabulary, copy-target structures with pointer-generator
  extended vocabulary, and resolution precedence.
- Implemented LSTM neural seq2seq model architecture:
  bidirectional LSTM encoder, Bahdanau additive attention decoder,
  pointer-generator copy mechanism, padded tensor batch collation, and
  shared adapter interface.
- Built interactive CLI demo with `--demo` flag running 3 showcase queries
  (easy projection, numeric filter comparison, graceful failure handling),
  supporting both `--model template` and `--model lstm` with formatted ASCII tables.
- Confirmed Blackwell GPU environment on HPC (`gpunode8`, NVIDIA RTX PRO 6000,
  98GB VRAM, CUDA 13.0, capability 12.0) via Slurm verification job `359139`
  passing 100% of tensor allocation and matrix multiplication checks.
- Conducted deep code audit and fixed 8 training & preprocessing bugs:
  1. Added per-epoch data shuffling with deterministic seeded RNG (`training.py`).
  2. Added missing `--device` and `--batch-size` CLI arguments (`run_lstm_comparison.py`).
  3. Ensured `batch_size` and `device` are tracked in the run manifest.
  4. Eliminated redundant re-tokenization in batch collation (`collation.py`).
  5. Fixed `CopyTarget` default value mutable dict typing (`preprocessing.py`).
  6. Added warning for empty training vocabularies (`preprocessing.py`).
  7. Corrected `CopyTarget` import and removed `# noqa: F821` (`adapter.py`).
  8. Fixed `forward_step` return type annotation (`model.py`).
- Formally designated the **Pointer-Generator LSTM as the Primary Baseline**
  for Part 2 per user direction, retaining the deterministic Template parser
  as the fallback/comparison baseline.
- Cancelled old GPU job `359338`, pulled all bug fixes to HPC repository,
  and resubmitted full two-stage GPU training job `359370` on Slurm
  (WikiSQL 56k warm-up 10 epochs + Spider 7k primary 10 epochs, batch size 64).
- Verified full test suite: 50 unit tests pass in 3.05s, Ruff clean.

## Current roadblocks

- Slurm GPU job `359370` is queued on `gpunode8` waiting for resource slice
  allocation under MPS (status PENDING, reason Resources).
- Part 2 report drafting (Sections a–d: Introduction, Literature Survey,
  Dataset & Preprocessing, Methodology & Comparative Baseline Results with
  Error Analysis) has not yet been authored.
- Full-dataset neural metrics for LSTM are pending job `359370` completion.

## Next immediate steps

1. Monitor Slurm job `359370` until completion, then retrieve checkpoints,
   training logs, and evaluation metrics via `scp`.
2. Run comparative evaluation on full WikiSQL (8,415) and Spider (1,034)
   dev sets using `scripts/run_lstm_comparison.py`.
3. Draft Part 2 report Sections a–d (Introduction, Literature Survey,
   Dataset/Preprocessing, Methodology & Comparative Baseline Results)
   including qualitative and quantitative error analysis.
4. Rehearse CLI demo and freeze Part 2 deliverables by September 30.

## Session metadata

| Field | Value |
|---|---|
| Last updated | 2026-09-22 |
| Active branch | `spec/agent-governance-rules` |
| Primary baseline | Pointer-Generator LSTM Seq2Seq |
| Fallback baseline | Deterministic Template Parser |
| Overall Part 2 completion | 85% |
| HPC Job ID | `359370` (`csis_gpu_lstm` on `gpunode8`) |
| Test suite status | 50 passed, 0 failed, Ruff clean |
| Next review point | GPU job completion & Part 2 report drafting |
