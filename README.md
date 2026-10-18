# CS F429 Natural Language Processing: Text-to-SQL Translation

This repository contains the codebase for the **Natural Language to SQL (Text-to-SQL)** project
for **CS F429 (Natural Language Processing)** at BITS Pilani.

The system translates natural language queries into executable SQLite SQL queries across both
single-table databases ([WikiSQL](https://github.com/salesforce/WikiSQL)) and complex, cross-domain
multi-table relational databases ([Spider](https://yale-lily.github.io/spider)).

---

## 1. System Architecture & Baselines

We implement and evaluate two classical baseline architectures in Part 2:

1. **Deterministic Rule-Based Template Parser (`TemplateBaseline`):**
   - Matches question tokens to schema tables/columns, detects literals, comparison, aggregation and ordering cues, and fills a single-table SQL template.
   - Never produces joins; abstains (empty prediction) when no confident single-table reading exists.

2. **Pointer-Generator LSTM Sequence-to-Sequence (`LSTMBaseline`):**
   - **Encoder:** 2-layer BiLSTM (256 per direction). **Decoder:** 2-layer LSTM (512) with additive attention.
   - **Pointer mechanism:** copy gate mixing the vocabulary distribution with attention over question and schema tokens.
   - **Inference pipeline:** schema-markup token mask → surface-form rendering ([`rendering.py`](src/text_to_sql/lstm/rendering.py)) → schema-aware repair ([`sql_repair.py`](src/text_to_sql/lstm/sql_repair.py)), configurable through `DecodeOptions`.

**Headline results (official Spider evaluator; full details, CIs and significance tests in [`docs/part-2-report.md`](docs/part-2-report.md)):**

| Spider test (held out, 2,147) | Official EX | Official EM |
|---|---:|---:|
| LSTM, final inference | 7.2% | 5.5% |
| LSTM, as submitted (Job 361547) | 6.8% | 5.2% |
| Template parser | 9.5% | 6.7% |

On Spider the template is the stronger baseline (significant by McNemar; borderline under a
database-clustered bootstrap). On WikiSQL the LSTM is far stronger (17.2% vs 2.7% EX). Both
fail on multi-table queries; the dominant error is schema linking.

### Part 3 (in progress, due 2026-11-21): modern models and novelty

3. **Fine-tuned T5-base (`T5Baseline`, [`transformer/`](src/text_to_sql/transformer/))**: input
   `question | db | table : col , ... | fk : ...`; `<` added to the vocabulary; checkpoint chosen by dev EX.
4. **Novelty (A + B):**
   - **A, schema-constrained decoding** ([`constrained.py`](src/text_to_sql/transformer/constrained.py)):
     beams that complete an identifier not in the schema, question or SQL keywords are pruned; finished
     candidates must compile under SQLite `EXPLAIN`.
   - **B, execution-guided correction** ([`exec_correction.py`](src/text_to_sql/generation/exec_correction.py)):
     rerank T5 beams by execution; for the LLM, feed SQLite errors back for at most 2 retries.
5. **gpt-oss-20b, instruction-tuned LLM (`GPTBaseline`, [`llm/`](src/text_to_sql/llm/))**: zero/few-shot,
   DAIL-SQL-style `CREATE TABLE` prompts with sample rows; run on the HPC in bf16.

**Spider dev (1,034), official evaluator** (gpt-oss test run pending):

| System | Official EX | Official EM |
|---|---:|---:|
| T5-base, beam | 54.1% | 52.1% |
| T5-base + A + B | **64.4%** | 59.5% |

**Spider test (2,147, held out, run once):** T5-base beam 53.4% EX / 49.6% EM; T5-base + A + B **62.4%** / 56.7%
(+9.0 EX, CI [7.3, 10.9], 196 fixed, 3 broken).
| gpt-oss-20b, 0-shot | 78.6% | 20.1% |

A + B vs beam: +10.3 EX, 95% database-clustered CI [7.5, 13.3], Holm-adjusted McNemar p = 1e-27
(110 questions fixed, 3 broken). Details: [`docs/part-3-error-analysis.md`](docs/part-3-error-analysis.md);
plan and checklist: [`docs/part-3-plan.md`](docs/part-3-plan.md); challenges:
[`docs/part-3-challenges.md`](docs/part-3-challenges.md); viva: [`docs/viva-day-checklist.md`](docs/viva-day-checklist.md).

---

## 2. Repository Layout

```text
├── docs/                             # Report and documentation
│   ├── part-2-report.{pdf,tex,md}    # Part 2 report (Sections a-d); md is the source
│   ├── error-analysis.md             # Quantitative and qualitative error analysis
│   └── *-design.md, system-architecture.md, tech-stack.md, text-to-sql-prd.md
├── scripts/                          # Execution and Slurm submission scripts
│   ├── hpc_run_lstm_gpu.sh           # HPC two-stage GPU training script (Job 361547)
│   ├── hpc_run_lstm_seed.sh          # Multi-seed replication (+ dev-loss curve, epoch-10 checkpoint)
│   ├── hpc_decode_seeds.sh           # GPU decoding of replication checkpoints
│   ├── hpc_decode_wikisql.sh         # GPU decoding of full WikiSQL dev
│   ├── run_lstm_comparison.py        # Training + dual-baseline evaluation runner
│   ├── run_ablation.py               # Inference ablation on one checkpoint (dev/test, Spider/WikiSQL)
│   ├── run_official_spider_eval.py   # Official Spider evaluator wrapper (exact-set match, EX)
│   ├── analyze_part2.py              # CIs, McNemar, error taxonomy, schema linking, gold sanity check
│   ├── generate_loss_plot.py         # Training / dev NLL figure
│   ├── show_preprocessing.py         # Preprocessing walkthrough and corpus statistics
│   ├── build_report.sh               # Markdown -> LaTeX -> PDF report build
│   └── run_part2_smoke.py            # Bounded smoke test runner
├── src/text_to_sql/                  # Core package
│   ├── baselines/                    # Deterministic template baseline
│   ├── data/                         # Typed contracts, SQLite introspection, Spider & WikiSQL loaders
│   ├── evaluation/                   # Read-only SQLite execution, metrics, statistics
│   ├── lstm/                         # Pointer-generator model, training, adapter, & SQL repair
│   ├── cli.py                        # Interactive CLI demonstration
│   └── config.py                     # Typed runtime configuration & deterministic seed helpers
├── tests/                            # pytest suite
├── data/                             # Dataset acquisition documentation (data/README.md)
└── pyproject.toml                    # Package definition and uv dependencies
```

---

## Quick start for evaluation (from the LMS download)

The code archive contains no data. Datasets, the trained checkpoint and the official evaluator
live outside the repository, under one directory (default `/Users/roshini/datasets/text-to-sql`;
override with `export TEXT2SQL_DATA_ROOT=/path/to/text-to-sql`):

```text
$TEXT2SQL_DATA_ROOT/spider/spider_data/{train_spider.json,dev.json,test.json,tables.json,test_tables.json,database/,test_database/}
$TEXT2SQL_DATA_ROOT/wikisql/data/{dev.jsonl,dev.tables.jsonl,dev.db,...}
$TEXT2SQL_DATA_ROOT/artifacts-lstm-gpu-run/lstm-checkpoint/{spider_checkpoint.pt,wikisql_checkpoint.pt,vocabulary.json}
$TEXT2SQL_DATA_ROOT/part3/t5-base-ex/best/{config.json,model.safetensors,tokenizer files,t5_config.json}   # Part 3 T5-base
$TEXT2SQL_DATA_ROOT/part3/gpt_answers.json            # gpt-oss-20b answers precomputed on the HPC
```

The Part 3 live training demo downloads `google-t5/t5-small` from Hugging Face on first use
(about 240 MB), then runs offline.

```bash
uv sync --extra modern                          # install the pinned environment (with Part 3 models)
uv run pytest                                   # unit tests
uv run text-to-sql-demo --train-demo            # live training (~2-3 min CPU), then evaluation
uv run text-to-sql-demo --demo --model template # scripted CLI showcase
uv run text-to-sql-demo --demo --model lstm     # same showcase with the trained LSTM
uv run text-to-sql-demo --demo --model both     # template vs LSTM, each checked against gold SQL
uv run --extra modern text-to-sql-demo --demo --model all       # + T5, T5 + A + B, gpt-oss (Part 3)
uv run --extra modern text-to-sql-demo --train-demo --model t5  # live t5-small training (~3 min)
scripts/viva_train_demo.sh                      # same training as a short HPC job, local fallback
uv run python -m scripts.show_preprocessing     # preprocessing walkthrough and corpus statistics
```

The final report is [`docs/part-3-report.pdf`](docs/part-3-report.pdf) (LaTeX source
[`docs/part-3-report.tex`](docs/part-3-report.tex)), built from
[`docs/part-3-report.md`](docs/part-3-report.md) by `scripts/build_report.sh`. The Part 2 report is
[`docs/part-2-report.pdf`](docs/part-2-report.pdf) (`scripts/build_report.sh part-2-report`).

## 3. Installation & Setup

We use [`uv`](https://github.com/astral-sh/uv) for fast, deterministic dependency management.

```bash
# Clone the repository
git clone <repo-url>
cd NLPproject

# Sync dependencies (Python 3.12, PyTorch, pytest, ruff)
uv sync

# Part 3 models (transformers, accelerate, sentencepiece)
uv sync --extra modern
```

---

## 4. Dataset Setup

Datasets are stored externally and referenced via environment variables. See [`data/README.md`](data/README.md) for full download instructions.

Set the dataset environment paths:

```bash
export TEXT2SQL_WIKISQL_SOURCE=/path/to/wikisql/dev.jsonl
export TEXT2SQL_WIKISQL_DATABASE_ROOT=/path/to/wikisql
export TEXT2SQL_SPIDER_SOURCE=/path/to/spider/dev.json
export TEXT2SQL_SPIDER_SCHEMA=/path/to/spider/tables.json
export TEXT2SQL_SPIDER_DATABASE_ROOT=/path/to/spider/database
export TEXT2SQL_ARTIFACT_DIRECTORY=artifacts/part2
export TEXT2SQL_SEED=42
```

---

## 5. Running the Baselines & CLI Demonstration

### Interactive Terminal Demo
To test queries interactively against live SQLite databases:

```bash
# Launch interactive mode
uv run text-to-sql-demo --demo

# Or specify a model and evaluate a single question
uv run text-to-sql-demo --model lstm --question "How many singers do we have?"

# Part 3: every system side by side on one question
uv run --extra modern text-to-sql-demo --model all --question "How many singers do we have?"
```

### Reproduce Smoke Evaluation
To run the bounded 25-example sanity smoke evaluation across WikiSQL and Spider:

```bash
uv run python scripts/run_part2_smoke.py
```

### Reproduce Full Comparative Evaluation
To evaluate both the Template Baseline and the trained Pointer-Generator LSTM on the full Spider validation set:

```bash
uv run python scripts/run_lstm_comparison.py
```

Inference ablation and held-out test evaluation on a trained checkpoint
(official scoring requires the external evaluator, see the report's Reproducibility section):

```bash
uv run python -m scripts.run_ablation --checkpoint <spider_checkpoint.pt> \
    --dataset spider --split test --with-template --output-dir <dir>
uv run python -m scripts.analyze_part2 --dataset spider --split test \
    --model lstm=<dir>/mask_render/predictions.jsonl --model template=<dir>/template/predictions.jsonl \
    --output-dir <analysis-dir>
```

Outputs will be saved under `artifacts/`:
- `evaluation.md`: Markdown summary tables with difficulty and structure breakdowns.
- `breakdowns.csv`: Deterministic CSV metrics per category.
- `predictions.jsonl`: Gold vs. predicted SQL statements for every example.

---

## 6. Testing & Code Quality

Run the test suite and linter:

```bash
# Run the unit tests
uv run pytest

# Check code formatting and linting
uv run ruff check .
```
