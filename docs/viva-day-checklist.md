# Viva Day Checklist (Part 3)

## The day before
- [ ] `squeue -u csisnlp_20` is empty; cancel any of my jobs (one GPU job per user, see challenge 10)
- [ ] `uv run pytest` passes on the laptop
- [ ] `uv run text-to-sql-demo --demo --model all` runs (about 25 s) and gpt answers show (no "NOT PRECOMPUTED")
- [ ] `LOCAL=1 scripts/viva_train_demo.sh` runs offline (about 3 min): turn Wi-Fi off and try it
- [ ] T5 checkpoint present: `$TEXT2SQL_DATA_ROOT/part3/t5-base-ex/best/config.json`
- [ ] gpt answers present: `$TEXT2SQL_DATA_ROOT/part3/gpt_answers.json`
- [ ] Laptop charged; terminal font large; colours visible on the projector

## Demo order (about 10 minutes)
1. **Live training** (rubric: training shown during the demo):
   `LOCAL=1 scripts/viva_train_demo.sh`, or `scripts/viva_train_demo.sh` to try the HPC first
   (falls back to the laptop if no GPU starts within 2 minutes).
   While it runs, show the full T5-base HPC log (job 398846: 25 epochs, 7,000 questions, dev EX per epoch).
2. **All systems side by side**: `uv run text-to-sql-demo --demo --model all`.
   Point out Case 3 (join: template refuses, LSTM fails, T5 succeeds) and
   Case 4 (plain T5 "no such column", T5 + A + B correct).
3. **Free question** from the examiners: `uv run text-to-sql-demo --model all --question "..."`
   (gpt-oss shows "NOT PRECOMPUTED" for new questions: it needs ~42 GB of GPU memory).
   The 25 questions in `docs/viva-questions.tsv` have gpt-oss answers precomputed; steer free
   questions towards them, or say plainly that gpt-oss runs only on the HPC.
4. **Results slide / report table**: dev ablation with CIs and McNemar, then the held-out test numbers.

## If something fails
- HPC unreachable or busy: the wrapper runs locally; or run `LOCAL=1` directly.
- T5 checkpoint missing: copy from `/home/csisnlp_20/artifacts/part3/t5-base-ex/best`.
- Anything else: `uv run text-to-sql-demo --demo --model both` (Part 2 path, no transformers needed).
