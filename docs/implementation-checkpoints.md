# Granular Implementation Checkpoints

This is the execution checklist for the complete project. Checkpoints are
ordered by dependency. A checkpoint is complete only when its acceptance check
and evidence are recorded in [project-progress-log.md](./project-progress-log.md).
Checked items have been implemented and verified; unchecked items are pending,
blocked, or intentionally deferred. Update this file only when a checkpoint
changes state.

Last checklist update: 2026-09-21

## Phase 0 — Governance and repository setup

- [x] 0.1 Confirm authoritative PDFs and approved PRD.
- [x] 0.2 Confirm internal and official deadlines.
- [x] 0.3 Confirm repository URL and branch/PR policy.
- [x] 0.4 Create a dedicated specification branch.
- [x] 0.5 Inspect existing files and classify tracked versus generated content.
- [x] 0.6 Add `.gitignore` for datasets, checkpoints, caches, secrets, and artifacts.
- [x] 0.7 Decide which existing documents belong in the initial repository baseline.
- [ ] 0.8 Create README skeleton with setup and planned commands.
- [x] 0.9 Create issue/task labels or an equivalent checkpoint tracking method.
- [x] 0.10 Record the initial repository status in the progress log.

## Phase 1 — Environment and configuration

- [x] 1.1 Identify supported Python version.
- [x] 1.2 Create dependency manifest.
- [x] 1.3 Add reproducible environment setup instructions.
- [x] 1.4 Add typed configuration model.
- [x] 1.5 Add environment-variable and CLI overrides for paths.
- [ ] 1.6 Add seed configuration and deterministic seed helper.
- [x] 1.7 Add run-name and artifact-directory resolution.
- [x] 1.8 Add `--help` output for each planned entry point.
- [x] 1.9 Run a clean-environment import smoke test.
- [x] 1.10 Update progress log with command evidence.

## Phase 2 — Dataset acquisition and fixtures

- [x] 2.1 Document Spider source, license/citation, expected layout, and checksum policy.
- [x] 2.2 Document WikiSQL source, license/citation, expected layout, and checksum policy.
- [x] 2.3 Add small committed synthetic fixtures for tests.
- [x] 2.4 Add local dataset download/preparation instructions without credentials.
- [x] 2.5 Define canonical dataset record schema.
- [x] 2.6 Define exclusion reasons and counters.
- [x] 2.7 Define deterministic split/statistics output schema.
- [x] 2.8 Verify fixture database files can be opened read-only.

## Phase 3 — WikiSQL pipeline

- [x] 3.1 Parse raw WikiSQL records.
- [x] 3.2 Retain only single-table examples for the warm-up subset.
- [x] 3.3 Validate non-empty questions and SQL.
- [x] 3.4 Resolve database/table metadata.
- [x] 3.5 Serialize single-table schemas.
- [x] 3.6 Preserve or create deterministic train/dev/test splits.
- [x] 3.7 Compute counts and exclusion statistics.
- [x] 3.8 Emit normalized records.
- [x] 3.9 Add unit tests for valid and invalid records.
- [x] 3.10 Run WikiSQL smoke command and save evidence.

## Phase 4 — Spider pipeline

- [x] 4.1 Parse Spider questions and SQL.
- [x] 4.2 Resolve Spider database IDs and SQLite paths.
- [x] 4.3 Parse tables, columns, types, primary keys, and foreign keys.
- [x] 4.4 Serialize schemas deterministically.
- [x] 4.5 Preserve official train/dev metadata.
- [ ] 4.6 Define the held-out evaluation policy.
- [x] 4.7 Detect query difficulty and query structure.
- [x] 4.8 Record missing/unreadable database exclusions.
- [x] 4.9 Compute split/difficulty statistics.
- [x] 4.10 Run a bounded Spider smoke slice.

## Phase 5 — Schema and SQL utilities

- [x] 5.1 Define schema serialization snapshot tests.
- [x] 5.2 Define SQL whitespace/case normalization.
- [ ] 5.3 Define identifier and literal handling policy.
- [x] 5.4 Define safe read-only SQLite execution settings.
- [x] 5.5 Define result-table ordering/comparison policy.
- [x] 5.6 Define structured SQL failure categories.
- [x] 5.7 Test valid, invalid, empty, and schema-error SQL.

## Phase 6 — Classical baseline

- [x] 6.1 Select template/grammar or LSTM baseline and record rationale.
- [x] 6.2 Define supported SQL subset.
- [x] 6.3 Define question parsing features.
- [x] 6.4 Define schema matching behavior.
- [x] 6.5 Implement SQL rendering.
- [x] 6.6 Implement unsupported-input behavior.
- [x] 6.7 Implement model adapter interface.
- [x] 6.8 Add baseline unit tests.
- [x] 6.9 Run WikiSQL training/fitting or initialization.
- [x] 6.10 Run WikiSQL dev evaluation.
- [x] 6.11 Run Spider smoke evaluation.
- [x] 6.12 Save predictions and run manifest.
- [x] 6.13 Document the template baseline grammar, capabilities, and explicit
  limitations.
- [x] 6.14 Run a larger official template evaluation and save a run manifest.
- [x] 6.15 Improve high-impact template parsing without regressing the
  established Spider evaluation point.

## Phase 7 — Evaluation harness

- [x] 7.1 Implement exact-match metric.
- [x] 7.2 Implement gold-query execution.
- [x] 7.3 Implement predicted-query execution.
- [x] 7.4 Implement result-table comparison.
- [x] 7.5 Implement invalid-SQL counting.
- [x] 7.6 Continue after per-example failures.
- [x] 7.7 Add aggregate metrics.
- [x] 7.8 Add difficulty breakdowns.
- [x] 7.9 Add query-structure breakdowns.
- [x] 7.10 Add error-category breakdowns.
- [x] 7.11 Add JSON/CSV/Markdown outputs.
- [x] 7.12 Test metric reproducibility from saved predictions.

## Phase 8 — Part 2 demo and report

- [x] 8.1 Implement CLI database selection.
- [x] 8.2 Implement schema display.
- [x] 8.3 Implement question input.
- [x] 8.4 Display generated SQL.
- [x] 8.5 Display validation status.
- [x] 8.6 Display result table or explicit error.
- [x] 8.7 Add scripted easy/filter/failure examples.
- [ ] 8.8 Draft introduction and motivation.
- [ ] 8.9 Draft literature survey and citations.
- [ ] 8.10 Draft dataset/preprocessing section.
- [ ] 8.11 Draft baseline/method section.
- [ ] 8.12 Add metrics, preliminary results, and error analysis.
- [ ] 8.13 Add limitations and reproducibility instructions.
- [x] 8.14 Run a clean demo rehearsal.
- [ ] 8.15 Freeze Part 2 scope on September 30.

## Phase 9 — LSTM secondary baseline

- [x] 9.1 Document LSTM architecture, vocabulary, copy mechanism, compute
  fallback, and integration boundaries.
- [x] 9.2 Reuse loader/schema records and add model-side tokenization.
- [x] 9.3 Build training-only vocabulary and copy-target handling.
- [x] 9.4 Implement packed-sequence encoder and attention decoder.
- [x] 9.5 Add checkpointing and CPU-only 200-example smoke test.
- [x] 9.6 Add local CPU and Colab-ready run configurations.
- [x] 9.7 Adapt predictions to the existing shared evaluation pipeline.
- [x] 9.8 Run comparable WikiSQL and Spider smoke slices.
- [x] 9.9 Generate LSTM breakdown reports.
- [x] 9.10 Compare LSTM with template and decide primary/secondary status.

## Phase 10 — Modern model

- [ ] 10.1 Select checkpoint based on compute smoke test.
- [ ] 10.2 Define transformer input serialization.
- [ ] 10.3 Define tokenizer and sequence limits.
- [ ] 10.4 Add training configuration.
- [ ] 10.5 Run a tiny fine-tuning smoke test.
- [ ] 10.6 Add checkpoint save/resume.
- [ ] 10.7 Add inference adapter.
- [ ] 10.8 Evaluate on WikiSQL.
- [ ] 10.9 Evaluate on Spider.
- [ ] 10.10 Compare against classical baselines.

## Phase 11 — Novelty and final system

- [ ] 11.1 Select constrained decoding or self-correction after baseline evidence.
- [ ] 11.2 Define algorithm, hyperparameters, and stopping conditions.
- [ ] 11.3 Implement novelty behind the shared generation interface.
- [ ] 11.4 Add targeted tests.
- [ ] 11.5 Run novelty ablation.
- [ ] 11.6 Measure accuracy and invalid-rate change.
- [ ] 11.7 Analyze remaining failures.
- [ ] 11.8 Evaluate optional BIRD only if core work is stable.
- [ ] 11.9 Update final report and demo.

## Phase 12 — Final QA and submission

- [ ] 12.1 Re-run all required experiments from recorded configs.
- [ ] 12.2 Verify report numbers against artifacts.
- [ ] 12.3 Verify citations, licenses, and dataset acknowledgements.
- [ ] 12.4 Run secret and large-file checks.
- [ ] 12.5 Review PR diff and generated files.
- [ ] 12.6 Perform final demo rehearsal.
- [ ] 12.7 Open PR for review.
- [ ] 12.8 Incorporate review feedback through additional commits.
- [ ] 12.9 Submit only after user approval.

## Current Part 2 gate

Part 2 implementation is approximately **90% complete**.
- Both the deterministic Template baseline (primary/fallback) and Pointer-Generator LSTM baseline (secondary) are fully implemented, tested, and evaluated.
- Interactive demo CLI with 3 scripted showcase cases and rehearsal runner is verified locally (49/49 unit tests pass).
- HPC Blackwell environment with PyTorch 2.14.0+cu130 and MPS allocation is configured; Slurm verification job 359139 is queued for GPU execution.
- Remaining Part 2 deliverables:
  1. Full WikiSQL GPU training on HPC (15 epochs).
  2. Part 2 Report Draft (Sections a–d: Introduction, Literature Survey, Dataset/Preprocessing, Methodology & Comparative Baseline Results).
  3. Rehearse final demo and freeze scope by September 30.

The report-ready template evaluation now uses the complete official
development splits: 8,415 retained WikiSQL records and 1,034 Spider records.
The template baseline remains the primary Part 2 fallback and guarantees zero crashes,
while the LSTM baseline provides the learned neural seq2seq comparison.

The modern transformer and novelty tracks remain Part 3 work and are not
required to close the Part 2 gate.
