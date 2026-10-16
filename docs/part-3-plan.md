# Part 3 Plan and Checklist

**Official deadline:** November 21, 2026, 23:55 IST (30 marks)
**Internal freeze:** November 14, 2026
**Branch:** `feature/part3-modern-models`
**Authority:** `(2026) CS F429 Project Description and Evaluation.pdf`, then `docs/text-to-sql-prd.md`

## Rubric (what the marks are for)

| Item | Marks | How we earn it |
|---|---:|---|
| Model's novelty | 3 | Schema-constrained decoding (A) + execution-guided correction (B); architecture and hyperparameters stated |
| Improvement | 3 | Ablation vs plain T5 on Spider dev/test with McNemar p-values |
| Results | 2 | Final table across all five systems + error analysis (Part 2 taxonomy) |
| Challenges | 2 | Report section: problems hit at each stage and how they were solved |
| Demo and viva | 20 | Live training shown, CLI with all models, gold-checked verdicts |

## Systems compared

1. Template parser (Part 2)
2. Pointer-generator LSTM (Part 2)
3. Fine-tuned T5-base (modern, main model)
4. T5-base + novelty A/B (improved)
5. gpt-oss-20b, zero-shot and few-shot (instruction-tuned LLM; open weights, on HPC). No OpenAI API runs: no key.

## Compute policy

All training, full decoding and evaluation runs go to the HPC (Slurm, `--gres=mps:50`,
header copied from `scripts/hpc_run_lstm_gpu.sh`). Local runs are limited to unit
tests, lint and the viva live-training demo.

## Checklist

### Phase 0: setup and research (Oct 17–20)
- [x] Create branch `feature/part3-modern-models`
- [x] Add optional `modern` dependency group (transformers, accelerate, sentencepiece)
- [x] T5 input serialization, `T5Baseline` adapter, fine-tuning loop, tests (`8cd283e`)
- [x] Handle `<` (and other characters missing from the T5 vocabulary) in tokenization
- [x] Literature check: PICARD, RESDSQL, DIN-SQL, DAIL-SQL, C3, gpt-oss Spider results; fix GPT prompt format
- [ ] HPC smoke job: transformers + CUDA import, t5-base forward pass, gpt-oss-20b load (job 398804 running)
- [x] Sync Part 3 code to HPC (rsync); HPC: torch 2.14.0+cu130, transformers 5.20.1, kernels 0.17.2, triton 3.8.0; models cached on login node

### Phase 1: modern baselines (Oct 21–27)
- [x] `scripts/hpc_run_t5.sh` written (not yet submitted): T5-base on Spider train, dev loss per epoch, best checkpoint kept
- [ ] `scripts/hpc_decode_t5.sh`: greedy and beam decoding on Spider dev
- [ ] Score T5 dev with the official evaluator (`run_official_spider_eval.py`, `official_per_example.py`)
- [x] `src/text_to_sql/llm/prompts.py` and `gpt_adapter.py` (local HF/vLLM backend)
- [x] `scripts/hpc_run_gptoss.sh` written (not yet submitted): gpt-oss-20b zero-shot and few-shot on Spider dev
- [ ] Optional: T5 on WikiSQL dev for the cross-dataset table

### Phase 2: novelty (Oct 28–Nov 7)
- [ ] `transformer/constrained.py`: schema prefix-trie `LogitsProcessor` + SQLite `EXPLAIN` check on finished beams (A)
- [ ] `generation/exec_correction.py`: beam reranking for T5, error-feedback retries for GPT (B)
- [ ] Unit tests for trie, constraint and retry stopping conditions (no GPU, no network)
- [ ] `scripts/run_part3_ablation.py` + HPC job: greedy / beam / +A / +B / +A+B on dev
- [ ] Tune beam size and retry budget on dev only
- [ ] Fallback if EX does not improve: report invalid-SQL reduction

### Phase 3: final evaluation (Nov 8–13)
- [ ] Spider test (2,147), run once per final system
- [ ] Stats: `official_stats.py` (clustered CIs, McNemar, Holm)
- [ ] Error analysis: difficulty, single vs multi-table, schema linking / join / aggregation / nesting
- [ ] Qualitative examples where novelty fixes or breaks a query
- [ ] CLI: `--model t5 | t5+novelty | gpt | all`; gold-checked `--demo`
- [ ] CLI: `--train-demo --model t5` (t5-small, one database, a few minutes)
- [ ] Copy final checkpoints from HPC to `$TEXT2SQL_DATA_ROOT`

### Phase 4: report, demo, viva (Nov 14–21)
- [ ] Freeze code (Nov 14)
- [ ] Report: complete sections e (experiments) and f (conclusion), novelty method, challenges section
- [ ] Build PDF via `scripts/build_report.sh` (LaTeX bonus), 6–10 pages
- [ ] Update README, `state.md`, `docs/project-progress-log.md`
- [ ] LMS bundle (`scripts/make_lms_bundle.sh`)
- [ ] Viva prep: extend `docs/viva-qa-prep.md` with Part 3 questions; rehearse demo end to end
- [ ] Submit by Nov 21, 23:55 IST

## Risks
- HPC CUDA/library mismatch for transformers or vLLM: caught in the Phase 0 smoke job.
- gpt-oss-20b too slow under mps:50: fall back to HF generate with batching, or a dev subset.
- Novelty gives no EX gain: report invalid-SQL rate reduction (accepted by the PRD).
