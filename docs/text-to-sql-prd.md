# Text-to-SQL System — Product Requirements Document

**Course:** CS F429 — Natural Language Processing  
**Project:** Translating natural-language questions into executable SQL  
**Status:** Approved project scope  
**Authoritative sources:** The attached course project description/rubric and `NLPpart1.pdf`

## 1. Product summary

The system enables a non-technical user to ask a question in English about a
relational database. Given the question and the target database schema, it
generates SQL, validates and executes the query against SQLite, and presents
the generated SQL and result table.

The project is also an experimental comparison of NLP generations:

1. A classical pre-transformer baseline.
2. A modern pretrained transformer model.
3. A novel improvement that measurably improves the modern baseline.

## 2. Goals and non-goals

### Goals

- Translate natural-language questions into executable SQL.
- Generalize across unseen database schemas using Spider.
- Establish a working WikiSQL warm-up pipeline before scaling to Spider.
- Compare a classical method and a modern neural method under the same evaluation.
- Measure exact-match accuracy, execution accuracy, and invalid-SQL rate.
- Analyze failures by difficulty, query structure, and error category.
- Deliver a reproducible GUI or CLI suitable for the course demonstrations.
- Add one technically justified novelty with an ablation and measured improvement.

### Non-goals

- Production-grade access control, multi-tenant hosting, or database administration.
- Supporting arbitrary database engines beyond the SQLite evaluation environment.
- Treating BIRD as a required benchmark. BIRD is optional after the core system works.
- Claiming that generated SQL is safe for unrestricted production execution.
- Building a conversational memory system unless it directly supports the required demo.

## 3. Users and primary use cases

### Target user

A non-technical user who knows what information is needed but does not know SQL.

### Core use cases

1. **Interactive query**
   - Select or load a supported SQLite database.
   - Enter a natural-language question.
   - View the generated SQL.
   - View validation/execution status and the result table.

2. **Dataset evaluation**
   - Load a fixed split and model checkpoint.
   - Generate one SQL candidate per example.
   - Compute exact-match, execution accuracy, and invalid-SQL rate.

3. **Error analysis**
   - Filter results by difficulty, single-table/join structure, and error category.
   - Inspect the question, schema, gold SQL, predicted SQL, and execution outcome.

## 4. Scope and requirements traceability

The following requirements map directly to the mandatory course components.

| ID | Requirement | Acceptance evidence |
|---|---|---|
| R1 | Dataset selection and justification | Dataset cards and report section describing domain, size, source, suitability, limitations, and preprocessing |
| R2 | Classical baseline | Trained LSTM or template/grammar baseline with recorded predictions and metrics |
| R3 | Modern baseline | Fine-tuned T5 or BERT-based schema-aware model with reproducible configuration |
| R4 | Model details | Architecture, tokenizer/embeddings, attention, hyperparameters, training strategy, libraries, and compute documented |
| R5 | Evaluation | Exact-match, execution accuracy, and invalid-SQL rate computed on common splits |
| R6 | Error analysis | Quantitative breakdowns and qualitative failure cases |
| R7 | Novel contribution | One constrained/syntax-aware decoding or execution-error self-correction method |
| R8 | Demonstration | GUI or CLI showing question → SQL → result table |
| R9 | Reporting | 6–10 page research-style report covering introduction, literature, data, method, experiments, conclusion |

## 5. Dataset requirements

### 5.1 Spider — primary benchmark

The core benchmark is Spider, a cross-domain Text-to-SQL dataset with 10,181
questions, 5,693 unique SQL queries, 200 databases, and 138 domains. It includes
SQLite databases and official training/development data. The project must preserve
the benchmark's cross-domain property and difficulty labels where available:
easy, medium, hard, and extra-hard.

### 5.2 WikiSQL — warm-up benchmark

WikiSQL is a simpler single-table benchmark used to validate ingestion, schema
serialization, training, inference, and evaluation before Spider. Only examples
whose reference query targets one table are in scope for the warm-up subset.

### 5.3 BIRD — optional robustness benchmark

BIRD may be evaluated after the Spider system is complete. It must not delay or
replace the required Spider deliverables.

### 5.4 Dataset record contract

Every retained example must contain:

```text
example_id
dataset
split
database_id
database_path
question
schema_text
gold_sql
difficulty
query_structure
```

`query_structure` must support at least `single_table` and `multi_table_join`.

### 5.5 Preprocessing

- Serialize table names, column names, column types, primary keys, and foreign keys.
- Tokenize questions using the selected model tokenizer where applicable.
- Normalize SQL only for comparison; preserve original SQL for reporting.
- Validate that question, schema, and gold SQL are non-empty.
- Exclude missing or unreadable database references and record an exclusion count.
- Report split sizes and difficulty distributions.
- Use official splits when provided; otherwise use a deterministic 80/10/10 split.

## 6. Proposed system architecture

```text
Dataset files
    ↓
Data loader and validator
    ↓
Schema serializer + normalized records
    ↓
 ┌──────────────────┬─────────────────────┐
 │ Classical model  │ Modern transformer  │
 └──────────────────┴─────────────────────┘
    ↓
 SQL post-processing and validation
    ↓
 SQLite execution adapter
    ↓
 Metrics, error analysis, and artifacts
    ↓
 CLI / Gradio / Streamlit demo
```

### Proposed module boundaries

```text
src/
  data/          # loaders, validation, schema serialization, split statistics
  models/        # classical and transformer model adapters
  generation/    # decoding, SQL normalization, validation, novelty methods
  evaluation/    # exact match, execution accuracy, invalid-SQL rate, reports
  demo/          # CLI or web interface
  config/        # typed experiment configuration
tests/
configs/
scripts/
artifacts/
```

The exact filenames may change during implementation, but model and evaluation
interfaces must remain stable so that every model uses the same harness.

## 7. Model requirements

### 7.1 Classical baseline

Implement one allowed classical baseline:

- A sequence-to-sequence LSTM parser, or
- A template/grammar-based parser.

The baseline must return exactly one SQL string for each input. If it cannot
produce a candidate, it must return an empty string; evaluation must count this
as invalid rather than aborting.

The baseline must be evaluated on WikiSQL development/test splits and on the
Spider official development split plus any permitted held-out/test split. If
the official Spider test labels are unavailable, the project must document the
chosen development-only or deterministic re-split evaluation policy rather than
claiming results on the hidden test set.

### 7.2 Modern model

Implement a fine-tuned T5 model or BERT-based schema-aware parser. The model
input must include both the natural-language question and serialized schema.
The configuration must record:

- Checkpoint and tokenizer
- Maximum input/output lengths
- Learning rate, batch size, epochs, warm-up, and seed
- Frozen versus trainable parameters
- Decoding strategy and beam settings
- Hardware and software versions

### 7.3 Shared model interface

Each model must expose equivalent operations:

```text
train(dataset, config) -> checkpoint/artifacts
predict(question, schema, config) -> one SQL string
evaluate(split, database_root, config) -> metrics/artifacts
```

## 8. Evaluation requirements

### Exact-match accuracy

Compare the predicted and reference SQL using the selected normalized/component
comparison procedure. Document normalization and note that equivalent SQL can
receive a false negative.

### Execution accuracy

Execute predicted and reference SQL against the same SQLite database and compare
their result tables. Handle execution errors explicitly. Document possible false
positives when different queries happen to return the same result.

### Invalid-SQL rate

Count predictions that are empty, syntactically invalid, reference missing schema
objects, or otherwise fail execution. A single invalid prediction must not stop
the evaluation run.

### Required reporting

For every model and split, report:

- Exact-match accuracy
- Execution accuracy
- Invalid-SQL rate
- Number of examples evaluated
- Number and type of execution failures

Break down results by:

- Easy, medium, hard, and extra-hard difficulty
- Single-table versus multi-table joins
- Error category: schema linking, syntax, join path, aggregation, nesting, or other

## 9. Novelty requirement

Select one primary novelty after baseline measurements:

### Option A — constrained/syntax-aware decoding

Restrict decoding using the target schema and SQL grammar to reduce invalid SQL
and invalid table/column references.

### Option B — execution-error self-correction

If generated SQL fails execution, feed the error and relevant schema context back
to a correction step and regenerate a bounded number of candidates.

The selected method must include:

- Architecture and algorithm description
- Hyperparameters and stopping conditions
- Comparison with the unmodified modern baseline
- Ablation identifying which component caused improvement
- Improvement measured on a fixed held-out split

Novelty is not accepted solely because it adds a component; it must produce
measurable improvement or a clearly justified reduction in invalid-SQL rate.

## 10. Demo requirements

The demo must support the following visible flow:

1. Choose or load a SQLite database.
2. Display or make available its schema.
3. Enter a natural-language question.
4. Generate one SQL query.
5. Show the SQL and validation status.
6. Execute valid SQL.
7. Display the result table or a clear execution error.

The demo should also support selecting the classical, modern, or improved model
when checkpoints are available. It must not silently convert errors into
successful-looking empty results.

## 11. Milestones and deliverables

### Phase 1 — Proposal

- Problem definition
- Motivation
- Dataset identification and justification
- Completion roadmap

### Phase 2 — Baseline and demo

- Spider/WikiSQL data pipeline
- Classical baseline
- Evaluation harness
- Initial metrics and error analysis
- Working GUI/CLI
- Report sections: introduction through baseline results

### Phase 3 — Full system and novelty

- Modern transformer
- Selected novelty method
- Comparative and ablation experiments
- Final error analysis and challenges
- Polished GUI/CLI
- Complete 6–10 page report

## 12. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Transformer training exceeds available compute | Modern model delayed | Start with WikiSQL, use a small checkpoint, cap sequence lengths, and preserve classical/demo progress |
| Spider schema linking is difficult | Low execution accuracy | Track schema-linking errors, serialize foreign keys, and use constrained decoding or self-correction |
| Exact-match understates semantic correctness | Misleading results | Report execution accuracy alongside exact match |
| Invalid SQL aborts evaluation | Missing or biased metrics | Catch per-example execution failures and record them as invalid |
| Dataset files are incomplete | Broken pipeline | Validate paths early and report exclusions |
| Novelty does not improve accuracy | Part 3 risk | Run a baseline first, compare both novelty options at design time, and include invalid-rate improvement as a meaningful target |
| Demo depends on unavailable checkpoints | Viva failure | Package a small working checkpoint or deterministic fallback demo using the same interface |

## 13. Definition of done

The core project is complete when:

- Spider and WikiSQL records pass validation and statistics are reproducible.
- A classical model produces predictions and metrics on required splits.
- A modern model produces predictions and metrics under the same harness.
- Exact-match, execution accuracy, and invalid-SQL rate are reported.
- Error analysis includes quantitative breakdowns and inspected examples.
- One novelty method has an ablation and measured comparison.
- The demo visibly performs question → SQL → result/error.
- Configuration, commands, checkpoints, metrics, and environment details are documented.
- The final report addresses every mandatory course component.

## 14. Open implementation decisions

These decisions remain intentionally open until smoke tests and available compute
are checked:

1. LSTM versus template/grammar classical baseline.
2. T5 checkpoint versus BERT-based schema-aware parser.
3. Constrained decoding versus execution-error self-correction.
4. Gradio/Streamlit web demo versus CLI-first demo.
5. Exact SQL comparison implementation, provided its behavior is documented and consistent.
