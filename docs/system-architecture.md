# Text-to-SQL System Architecture

**Status:** Part 2 implementation architecture  
**Scope:** Baseline and demo first; modern model and novelty plug in later

## 1. Architectural goals

- Keep ingestion, modeling, evaluation, and presentation independently testable.
- Use the same prediction and evaluation contracts for classical and modern models.
- Make datasets, model checkpoints, and paths configurable.
- Preserve raw inputs and generated artifacts for error analysis.
- Ensure one malformed prediction cannot terminate a full evaluation run.
- Keep the Part 2 baseline usable even if transformer training is delayed.

## 2. Logical architecture

```text
                    ┌─────────────────────────────┐
                    │ Dataset acquisition/config  │
                    └──────────────┬──────────────┘
                                   ↓
                    ┌─────────────────────────────┐
                    │ Load, validate, split data  │
                    └──────────────┬──────────────┘
                                   ↓
                    ┌─────────────────────────────┐
                    │ Schema serialization        │
                    │ question + schema + metadata │
                    └──────────────┬──────────────┘
                                   ↓
              ┌────────────────────┴────────────────────┐
              ↓                                         ↓
   ┌──────────────────────┐                 ┌──────────────────────┐
   │ Classical baseline   │                 │ Modern transformer   │
   │ template/grammar/LSTM│                 │ T5 or schema-aware   │
   └──────────┬───────────┘                 └──────────┬───────────┘
              └────────────────────┬────────────────────┘
                                   ↓
                    ┌─────────────────────────────┐
                    │ SQL normalization/validation│
                    └──────────────┬──────────────┘
                                   ↓
                    ┌─────────────────────────────┐
                    │ SQLite execution adapter    │
                    └──────────────┬──────────────┘
                                   ↓
                    ┌─────────────────────────────┐
                    │ Metrics + error analysis     │
                    └──────────────┬──────────────┘
                                   ↓
                    ┌─────────────────────────────┐
                    │ CLI / Gradio / Streamlit     │
                    └─────────────────────────────┘
```

## 3. Repository component boundaries

```text
src/
  config/       Typed configuration and environment/path resolution
  data/         Dataset loaders, validators, schema serialization, statistics
  models/       Classical and transformer adapters
  generation/   SQL rendering, normalization, validation, novelty hooks
  evaluation/   Metrics, SQLite execution, reports, error categories
  demo/         CLI first; optional web UI
tests/          Unit, fixture, integration, and smoke tests
configs/        Versioned non-secret experiment configurations
scripts/        Reproducible entry points
artifacts/      Local ignored outputs: predictions, metrics, logs, checkpoints
docs/           PRD, plans, architecture, progress, and report support
```

## 4. Core data contracts

### Dataset example

```text
ExampleRecord:
  example_id: string
  dataset: string
  split: train | dev | test
  database_id: string
  database_path: configured path
  question: non-empty string
  schema_text: non-empty serialized schema
  gold_sql: non-empty string
  difficulty: easy | medium | hard | extra-hard | unknown
  query_structure: single_table | multi_table_join | other
```

### Model prediction

```text
Prediction:
  example_id: string
  model_name: string
  predicted_sql: string
  generation_status: success | unsupported | failure
  failure_reason: optional structured value
  config_id: string
```

### Evaluation result

```text
EvaluationResult:
  exact_match_accuracy: float
  execution_accuracy: float
  invalid_sql_rate: float
  evaluated_count: integer
  execution_error_count: integer
  breakdowns: structured tables
  run_manifest: path/reference
```

## 5. Runtime flows

### Offline evaluation

1. Resolve a versioned configuration.
2. Load and validate the requested split.
3. Serialize each schema deterministically.
4. Call the selected model adapter once per example.
5. Persist predictions before metric calculation.
6. Normalize SQL for exact-match comparison.
7. Execute gold and predicted SQL in the intended database.
8. Record success or structured failure per example.
9. Write aggregate metrics and breakdown artifacts.

### Interactive demo

1. Resolve a configured database path selected by the user.
2. Load and display a schema summary.
3. Accept a question.
4. Generate one SQL candidate.
5. Validate the candidate against the selected schema/database.
6. Show SQL and validation status.
7. Execute only a valid candidate against the selected database.
8. Show a result table or explicit error.

## 6. Configuration and artifact rules

- Dataset roots, database roots, checkpoint paths, seeds, limits, and output
  directories must be configured, not embedded in source code.
- Configurations must identify dataset, split, model, seed, and run name.
- Each run writes a manifest containing the resolved configuration and software
  version information.
- Large datasets, checkpoints, generated predictions, and logs remain local or
  in approved artifact storage and are not committed by default.

## 7. Failure boundaries

- Invalid input records are excluded with a counted reason.
- Unsupported model constructions produce a visible unsupported status.
- Empty predictions count as invalid SQL.
- SQL execution errors are recorded per example and do not abort evaluation.
- Missing configuration or database paths fail fast with actionable messages.
- The demo never converts failures into empty successful result tables.

## 8. Part 2 versus Part 3

| Component | Part 2 | Part 3 |
|---|---|---|
| Data pipeline | Required WikiSQL and Spider smoke path | Scale and harden |
| Model | Classical baseline | Modern transformer |
| Evaluation | Required metrics and error analysis | Comparative final evaluation |
| Novelty | Interface only | Constrained decoding or self-correction |
| UI | CLI required; web optional | Full polished demo |

