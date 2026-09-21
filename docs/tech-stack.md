# Text-to-SQL Project Technology Stack

This document defines the proposed technology stack for the course project. A
choice is not final merely because it appears here; changes must be recorded in
the progress log and made configurable where practical.

## 1. Core language and runtime

| Area | Choice | Purpose |
|---|---|---|
| Language | Python 3.11+ (exact supported version to be verified) | Data, modeling, evaluation, and demo |
| Package management | `venv` plus a locked dependency file | Reproducible local setup |
| Formatting/linting | Ruff or the repository-approved equivalent | Fast static checks |
| Type checking | Pyright or mypy if compatible with the selected libraries | Catch interface errors |
| Testing | pytest | Unit, fixture, integration, and smoke tests |

The exact Python version and tools must be checked against the available
environment before implementation. Do not hardcode a local machine path.

## 2. Data and database

| Component | Technology | Use |
|---|---|---|
| Primary benchmark | Spider | Cross-domain Text-to-SQL evaluation |
| Warm-up benchmark | WikiSQL | Single-table pipeline validation |
| Optional benchmark | BIRD | Post-core robustness evaluation only |
| Database engine | SQLite | Dataset execution and result comparison |
| Tabular handling | Python standard library, `sqlite3`, and optionally pandas | Records and displayed result tables |
| Schema representation | Typed Python records plus deterministic text serialization | Shared model input |

Dataset roots, database roots, and artifact directories must come from
configuration or command-line arguments.

## 3. NLP and modeling

### Part 2 baseline

- Template/grammar-based parser is the recommended first baseline because it
  minimizes implementation and compute risk.
- A sequence-to-sequence LSTM remains an allowed alternative if the team selects
  it after a feasibility check.

### Part 3 modern model

- PyTorch for tensor computation and training.
- Hugging Face Transformers for tokenizer, checkpoint, fine-tuning, and inference.
- T5 or a BERT-based schema-aware parser, selected after a small compute smoke test.

Model checkpoint names, cache directories, maximum sequence lengths, batch sizes,
seeds, and learning rates must be configuration values rather than source-code
constants.

## 4. Evaluation and analysis

- SQL normalization: a documented deterministic normalization utility.
- Exact match: normalized/component comparison selected and tested for the project.
- Execution accuracy: read-only SQLite execution and deterministic result-table comparison.
- Invalid-SQL rate: explicit count of empty, malformed, schema-invalid, and failed queries.
- Analysis output: JSON/CSV for machines and Markdown tables for reports.
- Visualization: matplotlib/seaborn only if needed for report figures; do not add
  visualization dependencies before a concrete need exists.

## 5. Interface and demo

### Required low-risk path

- CLI implemented first.
- Standard input/arguments for question, database path, model/config, and output.
- Human-readable SQL, status, and result/error output.

### Optional presentation layer

- Gradio or Streamlit may wrap the stable CLI/service layer.
- The web UI must not contain separate model or evaluation logic.
- UI errors must remain explicit and must never look like successful empty results.

## 6. Development and collaboration

| Area | Technology/process |
|---|---|
| Version control | Git |
| Remote | `https://github.com/eightbits0211/Text-to-sql.git` |
| Branching | Dedicated `spec/*` or `feature/*` branches |
| Integration | Pull requests; no direct default-branch commits |
| Documentation | Markdown in `docs/` |
| Experiment tracking | Versioned configuration plus local run manifests |
| Artifacts | Local ignored outputs or approved artifact storage |

## 7. Compute and resource policy

- CPU is sufficient for fixtures, data validation, the classical baseline, and
  the CLI.
- GPU may be required for transformer fine-tuning.
- Colab or a university cluster may be used only with approved access and
  documented environment details.
- Training must support bounded smoke runs before full runs.
- Do not commit checkpoints or expose credentials/tokens.

## 8. Dependency decision rules

Before adding a package:

1. Confirm that the standard library or an existing dependency is insufficient.
2. Check license and maintenance suitability.
3. Record the reason in the dependency manifest or documentation.
4. Add a minimal version constraint compatible with the supported Python version.
5. Run the smallest import and behavior test.

## 9. Deferred choices

- Exact Python patch version.
- LSTM versus template/grammar baseline.
- T5 checkpoint versus BERT-based parser.
- Gradio versus Streamlit.
- Constrained decoding versus execution-error self-correction.

These choices must be resolved with evidence from smoke tests and available
compute, not silently hardcoded.

