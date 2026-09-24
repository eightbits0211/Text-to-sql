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
   - Extracts candidate column names and values via lexical token matching against database schema tables.
   - Synthesizes queries via deterministic SQL templates.
   - Evaluated as a high-precision, low-recall reference baseline (**5.80%** Execution Accuracy on Spider).

2. **Pointer-Generator LSTM Sequence-to-Sequence (`LSTMBaseline`):**
   - **Encoder:** Bidirectional LSTM capturing contextual question and schema representations.
   - **Decoder:** Unidirectional LSTM with Bahdanau additive attention.
   - **Pointer Mechanism:** Linear copy-distribution gate dynamically copying schema identifiers and query constants directly from the input text to combat out-of-vocabulary (`<unk>`) token loss.
   - **Schema-Aware Syntax Repair ([`sql_repair.py`](file:///Users/roshini/NLPproject/src/text_to_sql/lstm/sql_repair.py)):** Automatic literal quoting, identifier normalization, and table hallucination correction.
   - **Results on Spider Dev (1,034 examples):** **5.90% Execution Accuracy**, **3.29% Exact Match**, matching the published Yale Spider benchmark range (3.2%–5.4%).

---

## 2. Repository Layout

```text
├── docs/                             # Authoritative documentation and reports
│   ├── error-analysis.md             # Detailed quantitative & qualitative error case studies
│   ├── implementation-checkpoints.md # Granular progress tracking
│   ├── part-2-submission-plan.md     # Rubric and submission roadmap
│   └── project-progress-log.md       # Chronological engineering log
├── scripts/                          # Execution and Slurm submission scripts
│   ├── hpc_run_lstm_gpu.sh           # HPC two-stage GPU training script
│   ├── run_lstm_comparison.py        # Dual-baseline comparative evaluation runner
│   └── run_part2_smoke.py            # Bounded smoke test runner
├── src/text_to_sql/                  # Core package
│   ├── baselines/                    # Deterministic template baseline
│   ├── data/                         # Typed contracts, SQLite introspection, Spider & WikiSQL loaders
│   ├── evaluation/                   # Read-only SQLite execution engine & metrics
│   ├── lstm/                         # Pointer-generator model, training, adapter, & SQL repair
│   ├── cli.py                        # Interactive CLI demonstration
│   └── config.py                     # Typed runtime configuration & deterministic seed helpers
├── tests/                            # Comprehensive pytest test suite (63 unit tests)
├── data/                             # Dataset acquisition documentation (data/README.md)
└── pyproject.toml                    # Package definition and uv dependencies
```

---

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

Datasets are stored externally and referenced via environment variables. See [`data/README.md`](file:///Users/roshini/NLPproject/data/README.md) for full download instructions.

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

Outputs will be saved under `artifacts/`:
- `evaluation.md`: Markdown summary tables with difficulty and structure breakdowns.
- `breakdowns.csv`: Deterministic CSV metrics per category.
- `predictions.jsonl`: Gold vs. predicted SQL statements for every example.

---

## 6. Testing & Code Quality

Run the test suite and linter:

```bash
# Run all 63 unit tests
uv run pytest

# Check code formatting and linting
uv run ruff check .
```
