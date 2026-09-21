# LSTM Seq2Seq Baseline Design

## Status

- **Role:** Additive secondary classical baseline
- **Primary baseline remains:** Template/grammar parser
- **Implementation status:** A1 design completed and awaiting user review; no
  LSTM code is included in this checkpoint
- **Evaluation contract:** Existing typed records, prediction adapter,
  evaluator, reports, artifacts, and CLI remain unchanged

## 1. Purpose and scope

This model adds a trainable sequence-to-sequence baseline to the existing
Text-to-SQL system. It is intended to provide a meaningful intermediate point
between the deterministic template baseline and the planned transformer model:

```text
template/grammar baseline -> LSTM seq2seq baseline -> transformer model
```

The LSTM is not a replacement for the template baseline. The template model
remains the Part 2 deliverable of record until the LSTM has reproducible,
validated results. Both systems will be evaluated with the same
`ExampleRecord` inputs, prediction artifacts, SQLite execution policy, and
metric/reporting code.

The initial implementation targets WikiSQL first and Spider second. It must
support CPU-only smoke training on a laptop and a Colab-ready configuration for
larger experiments. Full Spider compositional coverage is an evaluation goal,
not a promise that the first CPU smoke model will solve joins, nesting, or set
operations reliably.

## 2. Model architecture

### 2.1 Encoder input

For each `ExampleRecord`, the encoder receives one token sequence formed from
the existing fields:

```text
<bos> question tokens <schema_sep> serialized schema tokens <eos>
```

The question is preserved verbatim apart from deterministic tokenization.
`schema_text` is the existing deterministic schema serialization; no new data
loader or alternate schema representation is introduced. Schema separators
identify table names, column names, types, and key annotations so the decoder
can attend to their positions.

### 2.2 Encoder

- Embedding dimension: **256** by default
- Hidden dimension: **512** by default
- Layers: **2** bidirectional LSTM layers
- Dropout: **0.2** between stacked recurrent layers
- Packed sequences: required for padded batches
- Projection: concatenate the final forward/backward states and project them to
  the decoder hidden-state size

The encoder output at every input position is retained for attention. The
bidirectional encoder gives the decoder access to both question context and
schema context while preserving a compact CPU-friendly design.

### 2.3 Attention decoder

The decoder is a 2-layer unidirectional LSTM with additive attention over all
encoder outputs. At each step it consumes:

```text
previous target token embedding + previous attention context
```

The decoder starts from the projected encoder state and generates target SQL
tokens until `<eos>` or a configured maximum target length. Teacher forcing is
used during training with a configurable ratio; evaluation uses greedy
decoding first, with beam search deferred until the greedy path is validated.

### 2.4 Target representation

Gold SQL is tokenized into a conservative SQL vocabulary that separates:

- SQL keywords (`SELECT`, `FROM`, `WHERE`, etc.)
- punctuation and operators
- numeric and quoted literals
- identifiers

The renderer joins decoded tokens into a SQL string and passes it through the
existing validation and execution path. The model must never bypass the
existing read-only evaluator.

## 3. Vocabulary and copy mechanism

### 3.1 Training-only vocabulary construction

The fixed vocabulary is built from the **training split only**. It includes:

- special tokens: `<pad>`, `<unk>`, `<bos>`, `<eos>`, `<schema_sep>`
- frequent question tokens
- SQL keywords, operators, and punctuation
- frequent target literals and identifiers subject to a configured cutoff

Development and test examples are never used to expand the fixed vocabulary.
This prevents vocabulary leakage and makes run manifests reproducible.

### 3.2 Extended vocabulary for schema identifiers

A fixed vocabulary alone cannot reliably emit unseen database-specific table
column names. The decoder therefore uses a pointer-generator output with an
explicit per-example extended vocabulary.

#### Source and extended-vocabulary contract

For one example, let the encoder source be
`x = (x_1, ..., x_S)` and let `V` be the fixed training-only vocabulary.
The example-specific extended vocabulary is:

```text
V_x = V union {x_i | x_i is not in V}
```

The source token sequence retains the exact surface text needed to reconstruct
quoted identifiers. Token normalization is used only for matching; copied
output uses the original source token text. Repeated source tokens map to one
extended-vocabulary entry, while their attention probabilities are summed.
Source positions are never allowed to copy padding tokens.

#### Distribution and switch

At decoder step `t`, additive attention produces encoder weights
`a_{t,i}` over non-padding source positions and context vector `c_t`. The
decoder computes:

```text
p_vocab = softmax(W_vocab [h_t ; c_t] + b_vocab)
p_copy(y) = sum_i where x_i = y of a_{t,i}
p_gen = sigmoid(w_g [h_t ; c_t ; e(y_{t-1})] + b_g)
p(y) = p_gen * p_vocab(y) + (1 - p_gen) * p_copy(y)
```

`p_vocab` is zero outside `V`; `p_copy` is zero for tokens absent from the
source. The final distribution is evaluated over `V_x`, with duplicate source
occurrences accumulated before normalization. This makes the generation/copy
decision learned at every decoding step rather than triggered by a brittle
hand-written rule.

#### Training targets and loss

Each target SQL token is mapped deterministically:

1. If its normalized form is in `V`, use its fixed vocabulary index.
2. Otherwise, if an exact normalized match exists in the source, use that
   example-specific copied-token index.
3. Otherwise map it to `<unk>` and record an `unresolvable_target_token`
   preprocessing event; do not silently substitute another identifier.

The training loss is ordinary teacher-forced negative log likelihood over the
final extended distribution:

```text
L = -sum_t mask_t * log(max(p_t(target_t), epsilon))
```

where `mask_t` excludes padding after `<eos>`. There is no separate
generation-loss/copy-loss sum; the mixture distribution is trained directly.
This avoids double-counting targets that are available both in the fixed
vocabulary and in the source. `<pad>` is never a valid target.

#### Decoding and failure behavior

Greedy decoding selects the highest-probability token from `V_x` at each step.
Fixed-vocabulary tokens are rendered from their canonical form; copied tokens
are rendered from their exact source surface form. Decoding stops at `<eos>` or
the configured maximum length. If `<unk>` is selected, the adapter records an
explicit `unknown_token`/`unsupported` status and does not present the output
as a successful prediction. The existing evaluator still determines whether
any emitted SQL is valid or executable.

The copy mechanism is deliberately limited to source tokens. It does not
invent arbitrary identifiers, alter the existing schema serializer, or bypass
the shared SQL validation and execution path.

#### Implementation checkpoints for this subsystem

The copy mechanism will be implemented and tested in separate bounded units:

1. Build a per-example extended vocabulary and source-position map.
2. Verify duplicate source-token attention is summed correctly.
3. Verify fixed-vocabulary targets take precedence over copying.
4. Verify unseen schema identifiers map to copy targets and round-trip exactly.
5. Verify unresolvable targets produce an explicit preprocessing event.
6. Verify the mixed distribution sums to one with padding masked.
7. Verify greedy decoding reconstructs generated and copied tokens.

If these tests cannot be made reliable before the CPU smoke gate, the fallback
is to keep the LSTM implementation behind the same adapter with copy decoding
disabled and report that restricted experiment explicitly; the template
baseline remains primary. Copy support must not be replaced by silent
identifier guessing.

## 4. Data preparation contract

The LSTM reuses:

- `WikiSQLLoader`
- `SpiderLoader`
- `ExampleRecord`
- deterministic schema serialization
- official train/dev/test split labels

Only a model-side preprocessing layer is added. It will tokenize
`question + schema_text` for encoder input and `gold_sql` for decoder targets.
It must preserve `example_id`, `database_id`, split, difficulty, and query
structure so prediction artifacts and report breakdowns remain compatible.

Training vocabulary and token statistics are saved with each run. A model
checkpoint is not valid without the vocabulary/preprocessing metadata used to
decode it.

## 5. Training and evaluation defaults

| Setting | Local CPU smoke | Colab-ready run |
|---|---:|---:|
| Dataset order | WikiSQL, then Spider | WikiSQL, then Spider |
| Training examples | 200-example smoke slice | Configurable full train split |
| Batch size | 8 or 16 | 32 where memory permits |
| Optimizer | Adam | Adam |
| Initial learning rate | 0.001 | 0.001, configurable |
| Gradient clipping | 1.0 | 1.0 |
| Encoder/decoder dimensions | 256 / 512 | 256 / 512 |
| Decode mode | Greedy | Greedy first; beam optional later |
| Checkpoints | Every configured N steps | Every configured N steps |
| Device | CPU | CUDA if available, CPU fallback |

The CPU smoke run is an acceptance test for the complete loop, not a quality
claim. Expected times are recorded as ranges after the first implementation
run because laptop CPU speed and sequence lengths vary. The design target is
minutes for the 200-example smoke loop, tens of minutes to a few hours for a
bounded local experiment, and hours rather than days for a Colab GPU
experiment.

## 6. Integration boundaries

The LSTM adapter will expose the same operational shape as the template
baseline:

- `fit(records)`
- `predict(record)`
- `predict_records(records)`
- `evaluate(records)` where appropriate

It will return prediction records consumable by the existing
`artifacts.py`, `metrics.py`, and `reports.py` code. No public interfaces in
the data loaders, evaluator, report generator, or CLI should be changed.
Model selection will be configuration-driven so the CLI can select either
baseline without duplicating evaluation logic.

## 7. Validation gates

Implementation proceeds only through bounded checkpoints:

1. **A1:** This architecture design is reviewed before model code.
2. **A2/A3:** Tokenization and training-only vocabulary tests pass, including
   unseen schema identifiers and copy targets.
3. **B2:** A 200-example CPU smoke run trains, checkpoints, reloads, decodes,
   and writes prediction artifacts without modifying the template path.
4. **C2/C3:** The same official smoke slices are evaluated through the shared
   evaluator, with JSON/CSV/Markdown breakdowns.
5. **D1:** LSTM and template results are compared side by side. The template
   remains primary if the LSTM is not comparable by the internal decision date.

Existing template tests and evaluation results are regression gates for every
LSTM change.

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| CPU training is slow | Tiny smoke slice, packed sequences, small batches, checkpoint resume |
| Schema identifiers are unseen | Pointer-generator copy distribution |
| SQL tokenization loses exact names | Preserve source token text and copy exact spans |
| LSTM underperforms templates | Keep template as primary and report LSTM honestly as secondary |
| GPU access remains paused | CPU fallback and Colab-ready configuration |
| Evaluation becomes incomparable | Reuse existing adapter, metrics, reports, and smoke slices |

## 9. Deferred decisions

The following are intentionally deferred until the smoke loop exists:

- beam width and length normalization
- scheduled sampling schedule
- label smoothing
- pretrained embeddings
- attention variant comparison
- full Spider training duration
- whether LSTM results are strong enough for primary-report status
