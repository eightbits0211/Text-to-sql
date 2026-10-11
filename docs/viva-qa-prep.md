# CS F429 Part 2 Viva Q&A & Demonstration Script

**Course:** CS F429 Natural Language Processing, BITS Pilani  
**Component:** Part 2 Milestone Viva & Evaluation Preparation  
**Project:** Natural Language to SQL Translation  

---

## 0. Viva Run Sheet (print this page)

### Before the viva (once, at home)
1. Download `Text-to-SQL-Part2-code.zip` from LMS and unzip it, for example to `~/viva/Text-to-SQL-Part2`.
2. In a terminal:
   ```bash
   cd ~/viva/Text-to-SQL-Part2
   uv sync                 # installs the exact environment (needs internet the first time)
   uv run pytest -q        # expect: 87 passed
   ```
3. Keep `~/datasets/text-to-sql` where it is; the code reads data and checkpoints from there.
4. Run every command below once, so nothing surprises you.

### During the viva (in this order)
| # | Command | Time | What you are showing |
|---|---|---|---|
| 1 | `uv run text-to-sql-demo --train-demo` | ~3 min | **Training, live** (the rubric asks for this): loss falling, before/after output, train vs held-out accuracy |
| 2 | `uv run text-to-sql-demo --demo --model template` | 5 s | Rule baseline: 2 successes + 1 safe refusal |
| 3 | `uv run text-to-sql-demo --demo --model lstm` | 30 s | The full HPC-trained LSTM on the same 3 questions |
| 4 | `uv run text-to-sql-demo --model lstm --question "How many singers do we have?"` | 20 s | Any question you or the examiner types |
| 5 | `uv run python -m scripts.show_preprocessing --no-stats` | 10 s | Preprocessing: question → tokens → schema → target tokens (vocab vs copy) |
| 6 | Open `docs/part-2-report.pdf` | — | Results tables (Section d.6), ablation (d.7), errors (d.9), loss curve (d.3) |

While command 1 runs (about 3 minutes), talk through the code tour below.

### If something goes wrong
- `uv: command not found` → `curl -LsSf https://astral.sh/uv/install.sh | sh`, then open a new terminal.
- "database not found" or "checkpoint not found" → the data folder moved. Run `export TEXT2SQL_DATA_ROOT=/path/to/text-to-sql`, then rerun.
- The training demo is slow → `uv run text-to-sql-demo --train-demo --epochs 20` (about 1 minute; the loss still drops clearly).
- An LSTM answer is wrong → that's expected and matches the report: the model mislinks columns (Section d.9). Say so.

---

## 0.1 Code Tour (how to explain the code in 5 minutes)

**One sentence:** *a question and a database schema go in; SQL comes out; we execute it on SQLite and compare the result with the gold query's result.*

Follow one example through the pipeline and open each file as you go:

| Step | File → function | What to say |
|---|---|---|
| 1. Load data | `src/text_to_sql/data/spider.py` → `load_spider()` | Reads Spider JSON, attaches each question's database file and schema, labels difficulty with the official Spider rules (`_classify_difficulty`), and records why any example is excluded. `wikisql.py` does the same for WikiSQL. |
| 2. Describe the schema | `data/schema.py` → `serialize_schema()` | Turns tables, columns, types and foreign keys into text the model can read (`table: singer / - Age [number] …`). |
| 3. Tokenise | `lstm/preprocessing.py` → `tokenize_example()`, `build_training_vocabulary()`, `build_copy_target()` | Splits the question, schema and SQL into tokens. Builds the vocabulary from *training* data only. For every example, adds its unseen words as copyable tokens (the pointer mechanism). |
| 4. Model | `lstm/model.py` → `Encoder`, `AdditiveAttention`, `PointerGeneratorDecoder.compute_output_distribution()` | The BiLSTM encoder reads question + schema. At each step the decoder attends over the input and mixes two distributions: *generate* a word from the vocabulary, or *copy* one from the input (the `p_gen` gate). |
| 5. Train | `lstm/training.py` → `train_smoke()` | Stage 1 on WikiSQL, Stage 2 on Spider, teacher-forced cross-entropy (NLL), Adam lr 1e-3, gradient clipping 1.0, checkpoints after each stage. `evaluate_nll()` gives the held-out loss curve. |
| 6. Decode | `lstm/adapter.py` → `decode_tokens()`, `postprocess()` | Greedy decoding with schema-type words masked out (`DecodeOptions`), then `rendering.py → render_sql()` restores spelling and quoting, then `sql_repair.py → repair_sql()` fixes syntax slips. |
| 7. Rule baseline | `baselines/template.py` → `TemplateBaseline.predict()` | Matches question words to columns, detects numbers, comparisons and aggregates, fills a single-table template, and refuses joins. |
| 8. Evaluate | `evaluation/metrics.py` → `execute_read_only()`, `evaluate_predictions()` | Runs gold and predicted SQL read-only on SQLite and compares the results: strict EX, official-style EX, string match, invalid rate with an error class. `statistics.py` adds CIs and McNemar tests. The official Spider evaluator gives exact-set match. |
| 9. Demo | `cli.py` → `main()`, `run_query()`; `lstm/train_demo.py` → `run_training_demo()` | The CLI you are running. |

**Likely "show me" questions:**
- *"Where is attention?"* → `model.py`, class `AdditiveAttention`, `forward()`: `v^T tanh(W_enc h + W_dec s)`, then softmax.
- *"Where is the copy mechanism?"* → `model.py`, `compute_output_distribution()`: `p_gen * P_vocab`, plus `(1 - p_gen) * attention` scattered onto the source-token ids (`scatter_add_`).
- *"Where is the loss?"* → `training.py`, `_compute_batch_loss()`: the negative log-probability of each gold token, averaged over non-padding positions.
- *"Where are the hyperparameters?"* → `training.py`, `TrainingConfig` (embedding 256, hidden 512, 2 layers, dropout 0.2, lr 1e-3, batch 64 on the HPC).
- *"How do you know the evaluation is correct?"* → the gold SQL scores 100% against itself; gold queries return real answers (this check caught the WikiSQL bug, report d.11); and the official Spider evaluator is used.
- *"What does your preprocessing do?"* → run command 5. Point out lower-casing, `'France'` becoming `france`, and that the copy mechanism never receives a training signal (report c.5).

---

## 1. Live Demonstration Workflow

### Step-by-Step CLI Execution
During the viva, run the reliable end-to-end template demonstration first:

```bash
# Activate virtual environment
uv sync

# Launch the interactive demonstration
uv run text-to-sql-demo --model template --demo
```

### Live Training Demonstration (rubric: "training of the model to be shown")

Run this first. It takes about 2–3 minutes on the laptop CPU:

```bash
uv run text-to-sql-demo --train-demo
```

What it shows, and what to say:
1. **Before training:** a probe question decoded by randomly initialised weights produces garbage (`pID pID …`).
2. **Training:** the per-epoch training and held-out NLL print live; training NLL falls from about 4.9 to about 0.1. *"This is the same pointer-generator architecture and training loop as our HPC model, just smaller (embedding 128, hidden 256) and on one database (95 questions), so it fits in the viva."*
3. **After training:** the same probe now produces sensible SQL (`SELECT AVG(HS) … FROM Player`).
4. **Memorisation vs generalisation:** about 15/20 correct on questions it trained on, about 0/11 on held-out questions. *"That gap is exactly what the full model shows on Spider: training NLL 0.04, but dev NLL rising after epoch 3."*
5. Query the model you just trained:
   ```bash
   uv run text-to-sql-demo --model lstm --checkpoint artifacts/train-demo/spider_checkpoint.pt \
     --database /Users/roshini/datasets/text-to-sql/spider/spider_data/database/soccer_2/soccer_2.sqlite \
     --question "What is the average training hours of all players?"
   ```

If asked about the real training run: it ran on the HPC (Slurm job 361547, RTX PRO 6000, 50 min); the logs and loss curves are in the report (§4.3). The same script, `scripts/hpc_run_lstm_seed.sh`, reproduces it.

### Preprocessing Walkthrough (rubric: "examples of preprocessing output")

```bash
uv run python -m scripts.show_preprocessing --example spider-dev-4 --no-stats
```

This prints the raw question, its tokens, the serialised schema, the encoder input and the target SQL tokens, each marked as generated from the vocabulary or copied. Talking point: on Spider train, 100% of target tokens are in the vocabulary, so the copy mechanism never receives a training signal. On dev, 8.7% of target tokens can only be copied.

### Three Scripted Showcase Scenarios

| Scenario | Model | Database | Query / Question | Expected Behavior / Explanation |
|---|---|---|---|---|
| **1. Easy / Single-Table Success** | Template | `concert_singer` | *"What are the names of all singers from France?"* | Generates valid SQL, executes it on SQLite, and prints the returned rows. Demonstrates schema matching, filtering, validation, and execution. |
| **2. Filtering Success** | Template | `concert_singer` | *"What are the names and ages of singers older than 30?"* | Generates valid SQL with projection and numeric comparison, then prints the result table. |
| **3. Diagnostic Unsupported Case** | Template | `concert_singer` | *"What is the stadium name and capacity for the concert with the highest attendance?"* | Returns an explicit unsupported/empty result instead of inventing a misleading join. Demonstrates safe failure handling. |

### Optional LSTM Diagnostic

If asked to demonstrate the learned baseline, run:

```bash
uv run text-to-sql-demo --model lstm --question "How many singers do we have?"
```

The current LSTM checkpoint may generate invalid SQL. This is intentional
evidence of the documented limitation, not a failed demonstration setup. State
that the template baseline is the reliable live-demo system and the LSTM is
the research baseline evaluated through the saved full-dev artifacts.

### Questions You Can Type Live

You can type a question interactively, but you should not claim that every
natural-language question is supported. The template baseline is deliberately
limited to schema-grounded single-table patterns; joins, nested queries,
complex `OR` logic, and unsupported constructions may be rejected. The LSTM
accepts arbitrary text but may produce invalid SQL, which is a documented
baseline limitation.

Use these tested template questions with the default `concert_singer` demo
database:

| Question | Demonstrates | Expected behavior |
|---|---|---|
| `How many singers are there?` | `COUNT(*)` aggregation | Successful count query; 6 rows are counted as one aggregate result |
| `List the names of singers from France.` | Projection plus equality filter | Successful query returning four names |
| `What are the names and ages of singers older than 30?` | Multiple projection columns plus numeric comparison | Successful query returning four rows |
| `Show the stadium names ordered by capacity.` | Table/column matching plus `ORDER BY` | Successful ordered result table |
| `What is the stadium name and capacity for the concert with the highest attendance?` | Unsupported multi-table reasoning | Explicit unsupported/empty result, not fabricated SQL |

Start interactive mode with:

```bash
uv run text-to-sql-demo --model template
```

For a controlled viva, prefer the first four questions for successful
walkthroughs and use the final question to demonstrate safe failure handling.

---

## 2. Anticipated Viva Questions & Model Answers

### Q1: Why did you choose both Spider and WikiSQL? Why not just one?
**Answer:**
> *"WikiSQL is a single-table benchmark spanning 26,000 tables. It serves as our curriculum warm-up (Stage 1) to teach the model basic SQL syntax, keyword placement, and literal copying without confounding multi-table join complexity. However, WikiSQL is too simple—it has zero cross-table joins, no nested subqueries, and only basic conjunctions.*  
> *Spider is our primary benchmark. It is a cross-domain, multi-table benchmark where test databases are completely unseen during training. It requires synthesizing complex SQL: joins, GROUP BY, HAVING, subqueries, and set operations. Combining both allows us to evaluate how well a semantic parser handles both isolated tables and complex relational schemas."*

---

### Q2: Why is Execution Accuracy preferred over Exact Match (EM)?
**Answer:**
> *"Exact Match compares the string tokens of the predicted SQL against the gold SQL. However, SQL is a declarative language with immense semantic flexibility:*
> 1. *Ordering of conditions in `WHERE` (e.g. `A = 1 AND B = 2` vs `B = 2 AND A = 1`) has 0% exact match, but 100% semantic identity.*
> 2. *Table aliasing (`FROM singer AS t1` vs `FROM singer`) or trailing punctuation (semicolons) fails exact match.*
> 3. *Equivalent SQL formulations (e.g., using `JOIN` vs a subquery `IN`) retrieve identical data.*
>
> *Execution Accuracy measures whether running the generated query on the underlying SQLite database produces the exact same tuple result table as the gold query. In our Spider dev set, 32 final-LSTM queries are execution-correct without matching the gold string. Execution also has false positives, though: some of the template's EX hits are coincidental. For example, it drops `WHERE age > 20` and still matches, because every singer is over 20. That is why we report the official component-wise exact-set match as well, and list test-suite accuracy as future work."*

---

### Q3: How does the Pointer-Generator network work, and why is it necessary?
**Answer:**
> *"In a standard Seq2Seq model, the decoder only generates words from a fixed pre-trained vocabulary $\mathcal{V}$. In Text-to-SQL, column names, table names, and literal values (e.g., proper nouns, dates, codes) change from database to database and are Out-Of-Vocabulary (OOV).*
> *The Pointer-Generator network computes a soft copy gate $p_{\text{gen}} \in [0, 1]$ at each decoding step using the decoder state, context vector, and input token. When $p_{\text{gen}}$ is high, it generates standard SQL keywords (`SELECT`, `FROM`, `WHERE`) from $\mathcal{V}$. When $p_{\text{gen}}$ is low, it uses the attention distribution to copy schema identifiers or query constants directly from the input text into the query. This is what allows zero-shot generalization to unseen schemas."*

---

### Q4: Why was the LSTM so poor on WikiSQL? Isn't that catastrophic forgetting?
**Answer:**
> *"No. Two things were wrong, and neither was the model. First, our evaluation harness: the official WikiSQL database stores columns as `col0…colN`, but our gold SQL used header names. SQLite silently treats an unknown double-quoted name as a string, so 71% of gold queries returned nothing, and 'empty matches empty' counted as correct. We found this by checking that gold queries return real answers, not just that gold matches gold. Second, rendering: multi-word column names came out unquoted. The run log also shows WikiSQL was scored with the Stage-1 checkpoint, before any Spider training, so forgetting is impossible. With both fixed, the same Stage-1 weights reach 17.2% EX against the template's 2.7%."*

---

### Q5: What are the main error categories?
**Answer:**
> *"We counted them over all 1,034 dev questions rather than picking anecdotes:*
> 1. *Schema linking dominates. 690 of 746 invalid queries reference a nonexistent column. Identifier recall is about 40%, and 83% of failures use the wrong table set.*
> 2. *A serialisation bug: the schema text includes column types (`Country [text]`), and the model copied `text` as a column name in 278 predictions. We now mask those tokens at decode time.*
> 3. *Joins and nesting: multi-table strict EX is 1.8%, and extra-hard is 0/166.*
> 4. *Aggregation errors appear in 167 failures.*
>
> *The masking and rendering fixes cut invalid SQL from 77% to 72%, but most of those queries become valid-but-wrong. That shows the bottleneck is grounding in the schema, not syntax."*

---

### Q6: How does Part 2 directly inform Part 3?
**Answer:**
> *"Schema linking is the bottleneck, so Part 3 uses a pre-trained encoder with explicit question–schema linking and foreign-key-aware decoding, plus grammar-constrained decoding (PICARD-style) for the remaining syntax errors. We also fix the protocol: early stopping on a database-disjoint split of Spider train, at least three seeds, the official evaluator, and McNemar tests against this baseline. Our numeric targets on Spider test are official EX ≥ 25%, multi-table EX ≥ 15% and invalid SQL ≤ 20%."*

---

### Q7: What do the training curves show?
**Answer:**
> *"Training NLL falls from 1.72 to 0.10 on WikiSQL and from 1.84 to 0.04 on Spider. Training loss alone is misleading, so in the replication runs we also logged teacher-forced Spider-dev NLL every epoch. It bottoms out around epoch 3 and then climbs steadily to 25. The model memorises the training databases; it does not transfer. Optimiser details: one Adam optimiser with constant LR 1e-3, batch 64, clipping at 1.0, dropout 0.2, no warm-up or schedule."*

---

### Q8: Why both a template and a learned baseline? Which is better?
**Answer:**
> *"They fail differently. On Spider the template is the better baseline: 9.5% vs 7.2% official execution accuracy on the held-out test set. That lead is significant by McNemar, but only borderline once we cluster questions by database, so I'd call it probable rather than decisive. On exact-set match they're statistically tied. On WikiSQL it reverses: the LSTM reaches 17.2% vs the template's 2.7%. Both fail on multi-table queries, and the LSTM's main problem is schema linking."*

### Q9: Does the copy mechanism actually work?
**Answer:**
> *"We measured it. When the gold token can only be copied from the input, the gate switches to copy mode 96% of the time, so it knows when to copy. But it puts only 17% probability on the correct input token, against 82% for normal vocabulary tokens. So it knows when to copy, but not what to copy, which is the same schema-linking problem again."*

---

## 3. High-Scoring Viva Strategy & Mindset

### The 4 Golden Rules for Your Viva:
1. **Lead with the Live Demo:** Open terminal, run `uv run text-to-sql-demo --model template --demo`. It runs in 2 seconds and shows 3 clear cases: single-table SELECT, WHERE filtering, and graceful rejection of unsupported joins. This immediately proves your code is working.
2. **Quote the literature exactly:** Yu et al. (2018), Table 2, database split, Seq2Seq+Copying scores 4.1% dev / 5.3% test exact match. Our LSTM scores 5.0% dev / 5.5% test official exact-set match. That is the same order of magnitude, under a newer evaluator and release. Do not cite a "3.2–5.4% band"; it is not in the paper.
3. **Turn Baseline Weaknesses into Part 3 Strengths:** Whenever asked about errors (e.g., column hallucinations or 77% invalid rate), explain the root cause and pivot to Part 3: *"This exact finding proves that sequential LSTMs lack relational inductive bias, motivating our Part 3 plan for schema-linking transformers and PICARD grammar decoding."*
4. **Speak the Language of the Rubric:** Use exact technical terms: *cross-domain evaluation*, *zero-shot schema generalization*, *execution accuracy vs exact match*, *pointer-generator copy gate*, *curriculum learning*, *McNemar test*, *held-out test split*. Avoid "catastrophic forgetting"; our own evidence refutes it (Q4).

