# CS F429 Part 2 Viva Q&A & Demonstration Script

**Course:** CS F429 Natural Language Processing, BITS Pilani  
**Component:** Part 2 Milestone Viva & Evaluation Preparation  
**Project:** Natural Language to SQL Translation  

---

## 1. Live Demonstration Workflow

### Step-by-Step CLI Execution
During the viva, run the live demonstration via the built-in entrypoint:

```bash
# Activate virtual environment
uv sync

# Launch the interactive demonstration
uv run text-to-sql-demo --demo
```

### Three Scripted Showcase Scenarios

| Scenario | Model | Database | Query / Question | Expected Behavior / Explanation |
|---|---|---|---|---|
| **1. Easy / Single-Table Success** | LSTM | `concert_singer` | *"How many singers do we have?"* | Generates `SELECT COUNT(*) FROM singer`. Executes immediately on SQLite returning the row count. Highlights successful pointer copying and aggregation. |
| **2. Medium Filtering with Disjunction** | LSTM | `concert_singer` | *"How many concerts are there in year 2014 or 2015?"* | Generates `SELECT COUNT(*) FROM concert WHERE year = 2014 OR year = 2015`. Demonstrates copying numeric literals and condition parsing. |
| **3. Diagnostic Multi-Table Failure** | LSTM | `concert_singer` | *"Show the stadium name and the number of concerts in each stadium."* | Generates a complex join clause (`JOIN singer ON ...`), but links mismatched foreign key tables. Demonstrates the absence of relational inductive bias in LSTMs, motivating Part 3's schema-linking transformers. |

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
> *Execution Accuracy measures whether running the generated query on the underlying SQLite database produces the exact same tuple result table as the gold query. In our Spider dev set, 28 examples (2.7%) achieved execution accuracy despite having different surface forms than the gold query."*

---

### Q3: How does the Pointer-Generator network work, and why is it necessary?
**Answer:**
> *"In a standard Seq2Seq model, the decoder only generates words from a fixed pre-trained vocabulary $\mathcal{V}$. In Text-to-SQL, column names, table names, and literal values (e.g., proper nouns, dates, codes) change from database to database and are Out-Of-Vocabulary (OOV).*
> *The Pointer-Generator network computes a soft copy gate $p_{\text{gen}} \in [0, 1]$ at each decoding step using the decoder state, context vector, and input token. When $p_{\text{gen}}$ is high, it generates standard SQL keywords (`SELECT`, `FROM`, `WHERE`) from $\mathcal{V}$. When $p_{\text{gen}}$ is low, it uses the attention distribution to copy schema identifiers or query constants directly from the input text into the query. This is what allows zero-shot generalization to unseen schemas."*

---

### Q4: Why is the LSTM baseline's execution accuracy 5.9% on Spider, when classical models scored >80% on WikiSQL?
**Answer:**
> *"This difference is well-documented in the literature. In WikiSQL, every query belongs to a single table, and models only need to classify which column to project and which values to filter—often achieved with sketch-based slot-filling models.*
> *In Spider, the database schemas at test time are completely unseen, and over 42% of queries require joins across multiple tables. In the seminal Yale Spider benchmark paper (Yu et al., EMNLP 2018), the authors evaluated standard Seq2Seq and Pointer-Network baselines without schema graphs, and they achieved between 3.2% and 5.4% Exact Match. Our baseline achieves **3.29% Exact Match** and **5.90% Execution Accuracy**, exactly matching the literature baseline.*
> *Furthermore, on single-table Spider queries, our LSTM achieves **9.38% execution accuracy**, proving that the model learns single-table semantics, but lacks the relational graph inductive bias required for multi-table joins."*

---

### Q5: What were the major error categories identified in your error analysis?
**Answer:**
> *"Our quantitative breakdown across the 1,034 Spider dev set queries revealed three main failure modes:*
> 1. *Schema Column Hallucination (62.1% invalid rate on Easy queries): The model learned the correct clause structure, but hallucinated column names (e.g., using `text` instead of `country`).*
> 2. *Multi-Table Join Hallucination: Multi-table execution accuracy was only 1.83% because sequential LSTMs cannot reliably trace foreign key edges without a schema graph.*
> 3. *Complex Nested Queries (0% on Extra-Hard): Pure autoregressive sequence decoders cannot maintain long-range hierarchical state for subqueries and set operations (UNION/INTERSECT).*
>
> *Additionally, we implemented schema-aware post-processing (`sql_repair.py`) which automated literal quoting and table alignment, reducing invalid queries by 10% on Spider and achieving 100% validity on WikiSQL."*

---

### Q6: How does Part 2 directly inform your Part 3 implementation?
**Answer:**
> *"The empirical baseline results provide the exact architectural requirements for Part 3:*
> 1. *To solve column hallucination: We will implement cross-attention schema linking, explicitly scoring question token-to-column alignments.*
> 2. *To solve join hallucination: We will adopt a relation-aware transformer (such as RAT-SQL or RESDSQL) that explicitly encodes foreign key relationships.*
> 3. *To solve syntax errors (77.6% invalid rate): We will implement constrained grammatical decoding (PICARD) to prune syntactically illegal tokens during beam search."*
