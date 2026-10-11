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
| Template parser | 9.5% | 0.0% (6.7% with identifier quotes removed) |

Both baselines are weak on multi-table queries; the LSTM and the template are statistically tied on strict execution accuracy (McNemar p = 0.45 on test).

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
```

```bash
uv sync                                         # install the pinned environment
uv run pytest                                   # unit tests
uv run text-to-sql-demo --train-demo            # live training (~2-3 min CPU), then evaluation
uv run text-to-sql-demo --demo --model template # scripted CLI showcase
uv run text-to-sql-demo --demo --model lstm     # same showcase with the trained LSTM
uv run python -m scripts.show_preprocessing     # preprocessing walkthrough and corpus statistics
```

The report is [`docs/part-2-report.pdf`](docs/part-2-report.pdf), built from
[`docs/part-2-report.md`](docs/part-2-report.md) by `scripts/build_report.sh`.

## 3. Installation & Setup

We use [`uv`](https://github.com/astral-sh/uv) for fast, deterministic dependency management.

```bash
# Clone the repository
git clone <repo-url>
cd NLPproject

# Sync dependencies (Python 3.12, PyTorch, pytest, ruff)
uv sync
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
uv run text-to-sql-demo --model lstm --dataset spider --question "How many singers do we have?"
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
