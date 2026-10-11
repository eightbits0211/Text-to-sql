# CS F429 Part 2 Viva Q&A & Demonstration Script

**Course:** CS F429 Natural Language Processing, BITS Pilani  
**Component:** Part 2 Milestone Viva & Evaluation Preparation  
**Project:** Natural Language to SQL Translation  

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
> *"No. Our earlier draft claimed that, and we withdrew it once we checked the run log. Job 361547 scored WikiSQL with the Stage-1 checkpoint, saved before any Spider training, so nothing could have been forgotten. Reading the predictions showed the real cause: they were sensible SQL in an unexecutable surface form. For example, `WHERE no.= 42` should be `WHERE "No." = 42`. Multi-word column names were unquoted and lower-cased, and multi-word literals were split. Fixing the rendering, with no retraining, raises WikiSQL EX substantially (report §4.11)."*

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
> *"They fail differently. The template is a conservative rule system. It never joins, abstains on about 9% of questions, and is the stronger system on official execution accuracy: 9.5% vs 7.2% on Spider test. The LSTM accepts any question and attempts joins and nesting, but it mislinks the schema. Once the template's identifier quoting is normalised, the template also leads on exact-set match (6.7% vs 5.5% on test). On strict EX the two are statistically tied (McNemar p = 0.45 on test). Our earlier claim that the LSTM 'surpassed' the template rested on a one-query difference, so we withdrew it."*

---

## 3. High-Scoring Viva Strategy & Mindset

### The 4 Golden Rules for Your Viva:
1. **Lead with the Live Demo:** Open terminal, run `uv run text-to-sql-demo --model template --demo`. It runs in 2 seconds and shows 3 clear cases: single-table SELECT, WHERE filtering, and graceful rejection of unsupported joins. This immediately proves your code is working.
2. **Quote the literature exactly:** Yu et al. (2018), Table 2, database split, Seq2Seq+Copying scores 4.1% dev / 5.3% test exact match. Our LSTM scores 5.0% dev / 5.5% test official exact-set match. That is the same order of magnitude, under a newer evaluator and release. Do not cite a "3.2–5.4% band"; it is not in the paper.
3. **Turn Baseline Weaknesses into Part 3 Strengths:** Whenever asked about errors (e.g., column hallucinations or 77% invalid rate), explain the root cause and pivot to Part 3: *"This exact finding proves that sequential LSTMs lack relational inductive bias, motivating our Part 3 plan for schema-linking transformers and PICARD grammar decoding."*
4. **Speak the Language of the Rubric:** Use exact technical terms: *cross-domain evaluation*, *zero-shot schema generalization*, *execution accuracy vs exact match*, *pointer-generator copy gate*, *curriculum learning*, *McNemar test*, *held-out test split*. Avoid "catastrophic forgetting"; our own evidence refutes it (Q4).

