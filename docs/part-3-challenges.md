# Part 3 Challenges Log

Running record for the report's Challenges section (rubric item d, 2 marks):
what went wrong, how it was found, and how it was solved. Newest last.

| # | Stage | Challenge | Evidence | Resolution |
|---|---|---|---|---|
| 1 | Tokenization | The T5 SentencePiece vocabulary has no `<`, so `<` and `<=` in gold SQL become `<unk>` and the model can never emit them | Tokenizer maps `<` to the unknown id | `add_sql_tokens` adds the missing characters and resizes the embeddings before fine-tuning (`transformer/training.py`) |
| 2 | Infrastructure | Hugging Face's Xet transfer returned 404 for the legacy `t5-base` model id on the HPC login node | `xet-read-token` 404 during `snapshot_download` | Use canonical ids (`google-t5/t5-base`) with `HF_HUB_DISABLE_XET=1`; pre-download on the login node, run jobs with `HF_HUB_OFFLINE=1` |
| 3 | Infrastructure | gpt-oss-20b's MXFP4 kernels are a separate Hub download that offline mode cannot resolve by version | Job 398813: "Version 1 of kernels-community/gpt-oss-triton-kernels is not available" | Cached the kernel; offline mode made overridable per job (`HF_HUB_OFFLINE=0`) |
| 4 | Infrastructure | MXFP4 kernels are compiled by Triton at load time, which needs `Python.h`; the Rocky Linux nodes do not have it (same root cause as the Part 2 `TORCH_DISABLE_NATIVE_JIT` issue) | Job 398845: gcc failed compiling Triton's `driver.c` | Load gpt-oss-20b dequantized to bf16 (`--dequantize`, ~42 GB, fits on the card) |
| 5 | Model selection | Dev NLL was lowest at epoch 2 of 25 and rose afterwards, but that checkpoint still produced degenerate SQL (e.g. repeated `avg(T2.avg(...`); NLL is a poor proxy for execution accuracy | Job 398812 history: dev loss 0.451 at epoch 2 to 0.792 at epoch 25 | Select the checkpoint by greedy dev execution accuracy each epoch (`--select-by ex`); final claims rest on the held-out test split, since dev is now used for selection |
| 6 | Novelty validation | A constraint that rejects correct SQL would hurt accuracy | Constraint run over all gold queries | Rejects 0/1,034 dev and 1/7,000 train gold queries; the one train query references `Ref_Company_Types`, a table missing from its database (a Spider annotation error) |
| 7 | Infrastructure | `sbatch --export=ALL,VAR="--shots 0,1"` splits on commas, so job arguments were silently truncated | Job 398865 ran only the 0-shot setting | One job per setting, with no commas in exported values |
| 8 | Compute budget | gpt-oss-20b in bf16 decodes about 0.3 questions/s (about 55 min per 1,034-question setting), so 0-shot plus 3-shot on full dev exceeds the 2-hour job limit | 25 s for 8 questions in job 398865 | One job per prompting setting (398898, 398899) |
| 9 | Model selection | Per-epoch dev EX is noisy (best 51.3% at epoch 14, neighbours 46-49%), so dev-selected numbers are optimistic | `history.jsonl` of job 398846 | Report dev for the ablation and make the headline claims on the held-out test split, run once |
