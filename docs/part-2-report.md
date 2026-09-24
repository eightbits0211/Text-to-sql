# CS F429 Natural Language Processing — Part 2 Project Report

**Title:** Robust Natural Language to SQL Translation Across Single- and Multi-Table Relational Databases  
**Course:** CS F429 Natural Language Processing, BITS Pilani  
**Component:** Part 2 Milestone Report (Classical Baselines, Empirical Benchmarks, & Error Analysis)  
**Date:** September 24, 2026  
**Status:** Frozen Baseline Implementation (Phase 2 Deliverable)  

---

## Abstract

Natural Language to SQL (Text-to-SQL) translation bridges the communication gap between non-technical domain users and relational databases. In this Part 2 milestone, we formulate the cross-domain semantic parsing task and construct an end-to-end evaluation harness for both single-table ([WikiSQL](https://github.com/salesforce/WikiSQL)) and complex multi-table relational databases ([Spider](https://yale-lily.github.io/spider)). We implement and empirically compare two classical baseline architectures: (1) a deterministic rule-based template parser and (2) a dual-stage Pointer-Generator BiLSTM sequence-to-sequence neural network equipped with Bahdanau attention, dynamic vocabulary copying, and schema-aware post-processing syntax repair. Evaluated across all 1,034 held-out Spider validation examples across 20 unseen database schemas, our optimized Pointer-Generator LSTM achieves **5.90% Execution Accuracy** and **3.29% Exact Match**, outperforming the deterministic template baseline (5.80% Execution Accuracy, 0.00% Exact Match) and falling directly within the canonical baseline band (3.2%–5.4% Exact Match) established in the seminal Yale Spider benchmark (*Yu et al., 2018*). On single-table queries, the model achieves **9.38% Execution Accuracy** and **5.88% Exact Match**, while achieving **100% syntactic validity** on WikiSQL. We present extensive quantitative breakdowns across official difficulty tiers (Easy: 13.31%, Medium: 4.04%, Hard: 5.75%, Extra-Hard: 0.00%) and six detailed qualitative error case studies, establishing a clear diagnostic foundation for modern schema-linking transformer architectures in Part 3.

---

## Section (a): Introduction & Task Formulation

### 1.1 Motivation and Practical Relevance
Relational database management systems (RDBMS) store the overwhelming majority of modern enterprise, transactional, and scientific data. Structured Query Language (SQL) is the standard query interface for retrieving and aggregating information from relational tables. However, authoring syntactically valid and semantically correct SQL requires substantial domain expertise: users must know SQL syntax conventions, understand relational algebra (projection, selection, grouping, Cartesian joins), and have detailed knowledge of database schemas, including exact table names, column names, data types, and primary-foreign key linkages.

The Text-to-SQL task seeks to automate this interface: translating arbitrary natural language questions $Q = (x_1, x_2, \dots, x_{|Q|})$ into executable SQL queries $Y = (y_1, y_2, \dots, y_{|Y|})$ that, when executed over database schema $\mathcal{S}$, retrieve the exact intended result table $\mathcal{R}$. Successfully solving this task democratizes database access for non-technical analysts, business users, and healthcare personnel, enabling intuitive conversational interfaces to structured data stores.

### 1.2 Core NLP Challenges in Text-to-SQL
Translating free-form human language into executable SQL entails multiple interrelated natural language understanding and formal semantic parsing challenges:

1. **Schema Grounding and Schema Linking:** Natural language questions rarely use exact database identifier names. For instance, the question *"Which airports are in Los Angeles?"* requires linking *"airports"* to table `AIRPORTS`, *"Los Angeles"* to column `City`, and retrieving `AirportCode` or `AirportName`. The system must bridge lexical gaps, synonyms, abbreviations, and informal phrasing to bind phrases to schema entities.
2. **Structural Compositionality and Complex Relational Logic:** Unlike single-table benchmarks where queries map to fixed templates (`SELECT agg(col) FROM t WHERE col = val`), multi-table relational benchmarks require synthesizing nested subqueries, aggregations (`COUNT`, `AVG`, `SUM`), group-by clauses with `HAVING` filters, ordering, bounds (`LIMIT`), and multiple `JOIN ... ON` constraints across complex foreign key hierarchies.
3. **Cross-Domain Generalization:** In real-world deployments, a model must generalize to unseen databases at test time without fine-tuning on target schemas (zero-shot domain transfer). The model must rely strictly on the schema metadata provided at inference time, precluding any memorization of table or column names.
4. **Constrained Syntactic and Execution Validity:** SQL is a strictly typed, formal language. A single misplaced parenthesis, an unquoted string literal (e.g. `WHERE city = Paris`), or a misspelled column identifier results in immediate SQLite compilation errors (`no such column`), yielding 0% execution utility even if 95% of the query tokens were semantically correct.

### 1.3 Mathematical Task Formulation
Formally, we define the Text-to-SQL problem as conditional sequence generation:

$$\hat{Y} = \arg\max_Y P(Y \mid Q, \mathcal{S})$$

Where:
- $Q = [q_1, q_2, \dots, q_m]$ is the sequence of natural language question tokens.
- $\mathcal{S} = (\mathcal{T}, \mathcal{C}, \mathcal{E})$ is the relational database schema, comprising tables $\mathcal{T} = \{T_1, \dots, T_k\}$, columns $\mathcal{C} = \{C_{i,j}\}$, and foreign key edges $\mathcal{E} \subseteq \mathcal{C} \times \mathcal{C}$. In serialized text format, $\mathcal{S}$ is represented as a linearized string sequence of table and column definitions.
- $Y = [y_1, y_2, \dots, y_n]$ is the target tokenized SQL query sequence drawn from an extended target vocabulary $\mathcal{V}_{\text{ext}} = \mathcal{V}_{\text{SQL}} \cup \mathcal{V}_{\text{schema}} \cup \mathcal{V}_{Q}$.

At each decoding timestep $t$, the conditional probability of predicting token $y_t$ is conditioned on the input representations and all previously emitted tokens $y_{<t}$:

$$P(Y \mid Q, \mathcal{S}) = \prod_{t=1}^n P(y_t \mid y_{<t}, Q, \mathcal{S})$$

---

## Section (b): Literature Survey & Related Work

### 2.1 Classical and Rule-Based Semantic Parsing
Early semantic parsers and conversational database interfaces relied heavily on pattern-matching rules, domain-specific grammars, and heuristic keyword mappers. Systems such as PRECISE (*Popescu et al., 2003*) mapped words to database elements by solving max-flow graph problems over bipartite schema matches. While PRECISE guaranteed 100% precision when a query was recognized, its recall degraded dramatically when queries deviated from anticipated linguistic patterns. Other classical approaches utilized Synchronous Context-Free Grammars (SCFG) (*Wong and Mooney, 2007*) or Combinatory Categorial Grammars (CCG) (*Zettlemoyer and Collins, 2005*), which induced formal lambda-calculus representations. Although theoretically sound, these systems required manual lexicon engineering and failed completely in cross-domain settings with unseen database schemas.

### 2.2 Sequence-to-Sequence Models & Neural Semantic Parsing
The advent of deep neural sequence-to-sequence (Seq2Seq) architectures (*Sutskever et al., 2014*; *Bahdanau et al., 2015*) fundamentally transformed Text-to-SQL. Instead of relying on brittle manual rules, recurrent neural networks (RNNs) with Long Short-Term Memory (LSTM) cells (*Hochreiter and Schmidhuber, 1997*) encoded question tokens into continuous vector representations and decoded sequential tokens auto-regressively.

Early neural attempts treated Text-to-SQL as standard machine translation. However, standard Seq2Seq models suffered from two fatal limitations:
1. **The Out-of-Vocabulary (OOV) Bottleneck:** Standard decoders sample exclusively from a fixed pre-trained vocabulary $\mathcal{V}$. In Text-to-SQL, queries frequently require database column names, table names, and literal values (e.g., proper nouns, dates, codes) that appear only in the input question or target schema and never in the training lexicon.
2. **Lack of Syntactic Constraints:** Standard sequential decoders are unaware of SQL grammar rules, frequently emitting malformed clauses, unclosed parentheses, or nonsensical keyword sequences.

### 2.3 Pointer Networks & Pointer-Generator Decoders
To solve the OOV bottleneck, *Vinyals et al. (2015)* introduced **Pointer Networks**, which use attention distributions directly as pointers to select positions in the input sequence. *See et al. (2017)* unified pointer mechanisms with generative decoders in **Pointer-Generator Networks**, which compute a soft generation-versus-copy probability:

$$p_{\text{gen}} = \sigma\left(W_h^\top h_t^* + W_s^\top s_t + W_x^\top x_t + b_{\text{ptr}}\right)$$

The final token probability distribution is a convex combination of the fixed vocabulary distribution and the input attention distribution:

$$P(w) = p_{\text{gen}} P_{\text{vocab}}(w) + (1 - p_{\text{gen}}) \sum_{i: w_i = w} a_i^t$$

This architecture allowed neural semantic parsers to dynamically copy schema identifiers, table names, and literal query values directly from the input prompt into the generated SQL, making zero-shot cross-domain generalization feasible.

In single-table contexts, *Zhong et al. (2017)* proposed **Seq2SQL**, combining Seq2Seq with pointer networks and reinforcement learning rewards to execute single-table aggregation and condition queries over WikiSQL. Concurrently, *Xu et al. (2017)* introduced **SQLNet**, which replaced end-to-end autoregressive decoding with a sketch-based slot-filling approach tailored specifically to single-table schemas.

### 2.4 Multi-Table Cross-Domain Benchmarks & Modern Transformer Evolution
While single-table models achieved high accuracy on WikiSQL (>80%), they proved wholly inadequate for real-world enterprise databases. To challenge the community, *Yu et al. (2018)* introduced **Spider**, a complex, cross-domain, multi-table Text-to-SQL benchmark spanning 200 databases, 10,181 natural language questions, and 5,693 distinct complex SQL queries. The original Spider paper evaluated multiple classical Seq2Seq and Pointer-Network baselines, demonstrating that without schema-linking graphs or relational inductive biases, Seq2Seq LSTMs achieved only **3.2% to 5.4% Exact Match** on held-out Spider dev sets.

Subsequent advancements bridged this gap through transformer-based pre-training and schema-graph encoding:
- **RAT-SQL** (*Wang et al., 2020*): Introduced relation-aware self-attention, encoding schema tables, columns, and foreign-key edges directly into the transformer self-attention layers.
- **T5 and Schema Pruning (RESDSQL)** (*Li et al., 2023*): Utilized large language models (T5-3B) coupled with decoupled schema-ranking classifiers to filter irrelevant tables before generation.
- **Constrained Decoding (PICARD)** (*Scholak et al., 2021*): Enforced strict grammatical and schema validity at every decoding beam step via incremental SQLite abstract syntax tree parsing.

In this project, our Part 2 baseline implements the canonical Pointer-Generator Seq2Seq LSTM baseline, establishing the rigorous empirical floor that motivates Part 3's transformer and schema-linking innovations.

---

## Section (c): Dataset Description, Preprocessing & Serialization

### 3.1 Dataset Selection & Scope

To rigorously train and evaluate our classical baselines, we utilize two authoritative benchmarks:

| Characteristic | WikiSQL (*Zhong et al., 2017*) | Spider (*Yu et al., 2018*) |
|---|---|---|
| **Primary Focus** | Single-table warm-up & sanity baseline | Complex, cross-domain multi-table primary benchmark |
| **Number of Databases** | 26,575 isolated tables | 200 multi-table relational databases |
| **Domains** | Wikipedia tabular articles | 138 diverse enterprise & academic domains |
| **Relational Operations** | Simple `SELECT`, `WHERE` (AND only), basic aggregations | Joins, `GROUP BY`, `HAVING`, `ORDER BY`, `LIMIT`, `UNION`, `INTERSECT`, `EXCEPT`, subqueries |
| **Cross-Table Joins** | 0% (Single table per database) | >42% of validation queries require joins across $\ge 2$ tables |
| **Split Strategy** | Table-split (unseen tables at test time) | Database-split (unseen database schemas at test time) |
| **Role in Project** | Stage 1 curriculum warm-up (55,968 train) | Stage 2 primary baseline training (7,000 train, 1,034 dev) |

### 3.2 Schema Serialization Contract
In multi-table Text-to-SQL, the model must condition on both the question $Q$ and the schema $\mathcal{S}$. We designed a deterministic, typed schema serializer in [`schema.py`](file:///Users/roshini/NLPproject/src/text_to_sql/data/schema.py) that introspects SQLite catalogs and generates a standardized textual schema representation:

```text
Table: customers | Columns: id (integer, PK), name (text)
Table: orders | Columns: id (integer, PK), customer_id (integer) | Foreign Keys: customer_id -> customers.id
```

The unified prompt input to the encoder concatenates the question and linearized schema separated by special delimiter tokens:

$$\mathbf{X} = [\text{<sos>}] \circ Q \circ [\text{<sep>}] \circ \mathcal{S} \circ [\text{<eos>}]$$

### 3.3 Tokenization, Vocabulary Construction & Copy Target Alignment
Standard word tokenizers split SQL tokens erratically. In [`preprocessing.py`](file:///Users/roshini/NLPproject/src/text_to_sql/lstm/preprocessing.py), we implemented a specialized regex-based SQL lexer that preserves SQL punctuation, table-column dot notations (`table.column`), and quoted string literals:

1. **Fixed SQL Vocabulary ($\mathcal{V}_{\text{vocab}}$):** Extracted across all training splits using a frequency threshold of 2, augmented with SQL reserved keywords (`SELECT`, `FROM`, `WHERE`, `JOIN`, `ON`, `GROUP`, `BY`, `HAVING`, `ORDER`, `LIMIT`, `ASC`, `DESC`, `AND`, `OR`, `NOT`, `IN`, `LIKE`, `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`, `UNION`, `INTERSECT`, `EXCEPT`). Total fixed vocabulary size: **1,402 tokens**.
2. **Dynamic Copy Vocabulary ($\mathcal{V}_{\text{copy}}$):** For each training and inference example, question tokens and schema identifiers that do not exist in $\mathcal{V}_{\text{vocab}}$ are assigned temporary dynamic indices offset by $|\mathcal{V}_{\text{vocab}}|$. Target SQL tokens matching any input token are mapped to their corresponding input source position, enabling supervised cross-entropy loss over both generated and copied tokens.

### 3.4 Official Spider Difficulty Classification
To evaluate structural query complexity, we implemented [`_classify_difficulty(sql_dict)`](file:///Users/roshini/NLPproject/src/text_to_sql/data/spider.py) strictly following Yale Spider's official evaluation benchmark (`eval_hardness`):
- **Component 1 ($C_1$):** Number of `WHERE`, `GROUP BY`, `ORDER BY`, `LIMIT`, `JOIN` (calculated as $\max(0, |\mathcal{T}_{\text{units}}| - 1)$), `OR`, and `LIKE` clauses.
- **Component 2 ($C_2$):** Number of nested subqueries and set operations (`INTERSECT`, `UNION`, `EXCEPT`).
- **Others ($C_o$):** Total count of aggregations across all clauses ($>1$), multiple projection columns ($>1$), multiple `WHERE` conditions ($>1$), and multiple `GROUP BY` columns ($>1$).

The four official difficulty tiers are defined as:
- **Easy:** $C_1 \le 1 \land C_o = 0 \land C_2 = 0$
- **Medium:** $(C_o \le 2 \land C_1 \le 1 \land C_2 = 0) \lor (C_1 \le 2 \land C_o < 2 \land C_2 = 0)$
- **Hard:** $(C_o > 2 \land C_1 \le 2 \land C_2 = 0) \lor (2 < C_1 \le 3 \land C_o \le 2 \land C_2 = 0) \lor (C_1 \le 1 \land C_o = 0 \land C_2 \le 1)$
- **Extra-Hard:** All queries exceeding the above thresholds.

The resulting distribution across the 1,034 Spider validation examples is:
- **Easy:** 248 examples (24.0%)
- **Medium:** 446 examples (43.1%)
- **Hard:** 174 examples (16.8%)
- **Extra-Hard:** 166 examples (16.1%)
- **Unknown:** 0 examples (0.0%)

---

## Section (d): Methodology, Baseline Architectures, Experimental Results & Error Analysis

### 4.1 Classical Baseline 1: Deterministic Template Parser
The deterministic template baseline ([`template.py`](file:///Users/roshini/NLPproject/src/text_to_sql/baselines/template.py)) acts as our high-precision reference floor:
1. Introspects database schema tables and columns.
2. Identifies projection targets by performing fuzzy token matching between question tokens and column names.
3. Detects explicit numeric literals, quoted strings, and comparison keywords (`greater than`, `less than`, `before`, `after`, `equal`).
4. Infers basic aggregations (`how many` $\to$ `COUNT`, `average` $\to$ `AVG`, `highest` $\to$ `MAX`).
5. Synthesizes a canonical single-table SQL query.

If question tokens do not match schema columns with high confidence, the template parser returns an empty prediction rather than hallucinating invalid SQL. On the Spider dev set, it achieves **5.80% Execution Accuracy** and **0.00% Exact Match**, with an invalid SQL rate of just **0.58%**.

### 4.2 Classical Baseline 2: Pointer-Generator LSTM Sequence-to-Sequence
Our primary baseline ([`model.py`](file:///Users/roshini/NLPproject/src/text_to_sql/lstm/model.py)) implements an autoregressive sequence-to-sequence neural network with pointer-generator attention:

```
[ Natural Language Question Q + Linearized Schema S ]
                     │
                     ▼
       ┌───────────────────────────┐
       │   Bidirectional LSTM      │  (2 layers, hidden_dim = 512,
       │        Encoder            │   embedding_dim = 256, dropout = 0.3)
       └─────────────┬─────────────┘
                     │ Encoder Hidden States H = [h_1, ..., h_m]
                     ▼
       ┌───────────────────────────┐
       │ Bahdanau Additive Attn    │  e_t,i = v_a^T tanh(W_s s_t + W_h h_i)
       │         Mechanism         │  a_t = softmax(e_t)
       └─────────────┬─────────────┘
                     │ Context Vector c_t = sum(a_t,i * h_i)
                     ▼
       ┌───────────────────────────┐
       │   Unidirectional LSTM     │  (2 layers, hidden_dim = 512)
       │        Decoder            │  s_t = LSTM(s_{t-1}, [y_{t-1}; c_t])
       └─────────────┬─────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
┌──────────────────┐   ┌──────────────────┐
│ Vocabulary Head  │   │  Pointer Head    │
│ P_vocab(w)       │   │  P_copy(w)       │
└─────────┬────────┘   └────────┬─────────┘
          │                     │
          └──────────┬──────────┘
                     ▼
   Copy Gate p_gen = sigma(w^T [s_t; c_t; x_t] + b)
   Final Distribution: P(y_t) = p_gen * P_vocab + (1 - p_gen) * P_copy
                     │
                     ▼
   Auto-regressive Greedy Decoding with <pad>/<unk> Masking
                     │
                     ▼
       ┌───────────────────────────┐
       │ Schema-Aware SQL Repair   │  Literal quoting, table re-alignment,
       │     (sql_repair.py)       │  parentheses balancing, identifier quoting
       └─────────────┬─────────────┘
                     │
                     ▼
       [ Executable SQLite SQL Query ]
```

#### Detailed Architecture Specifications:
- **Encoder:** 2-layer Bidirectional LSTM. Input embedding dimension $d_{\text{emb}} = 256$, hidden state dimension $d_{\text{enc}} = 512$ per direction (concatenated bidirectional hidden state $H_i \in \mathbb{R}^{1024}$).
- **Decoder:** 2-layer Unidirectional LSTM with hidden dimension $d_{\text{dec}} = 512$. Initialized from linearly projected encoder final states.
- **Attention:** Bahdanau additive attention computing alignment score $e_{t,i} = v_a^\top \tanh(W_s s_t + W_h h_i + b_a)$ and context vector $c_t = \sum_i \alpha_{t,i} h_i$.
- **Pointer-Generator Gate:** $p_{\text{gen}} = \sigma(W_{\text{ptr}}^\top [s_t; c_t; y_{t-1}] + b_{\text{ptr}})$, dynamically blending vocabulary distribution $P_{\text{vocab}}$ with source attention distribution $P_{\text{copy}}$.

### 4.3 Schema-Aware SQL Post-Processing & Syntax Repair
Raw seq2seq outputs frequently suffer from superficial formatting flaws that cause SQLite syntax errors. We developed [`sql_repair.py`](file:///Users/roshini/NLPproject/src/text_to_sql/lstm/sql_repair.py) to resolve these deterministic errors before execution:
1. **Literal Auto-Quoting:** Identifies comparison predicates (`=`, `!=`, `<`, `>`, `LIKE`) containing unquoted alphanumeric values (e.g. `WHERE country = France`) and automatically encloses them in single quotes (`'France'`).
2. **Identifier Quoting:** Encloses multi-word column names with spaces or slashes (e.g. `school/club team`) in double quotes (`"school/club team"`).
3. **Table Hallucination Correction:** When a query references non-existent tables, the repair engine re-aligns the table token to the schema table sharing the highest column overlap.
4. **Parentheses & Punctuation Balancing:** Automatically cleans malformed trailing conjunctions (`WHERE ... AND`), balances unclosed parentheses, and normalizes dots (`t1 . col` $\to$ `t1.col`).

### 4.4 Training Strategy & Compute Environment
Training was executed on the BITS Pilani HPC cluster (`gpunode8`) under Slurm Job ID **`361547`**:
- **Hardware:** 1$\times$ NVIDIA A100-PCIE-80GB GPU, 8 CPU cores, 32GB RAM.
- **Curriculum Training Strategy:**
  - **Stage 1 (WikiSQL Warm-up):** 55,968 examples, 10 epochs (8,740 optimization steps), batch size 64, Adam optimizer, initial learning rate $\eta = 10^{-3}$, linear warmup over 500 steps with cosine decay, gradient clipping at $\|\mathbf{g}\|_2 \le 1.0$. Training loss converged from $1.72 \to 0.10$. Saved as `wikisql_checkpoint.pt`.
  - **Stage 2 (Spider Primary):** 7,000 examples, 25 epochs (2,750 optimization steps), batch size 64, learning rate $\eta = 5 \times 10^{-4}$ with epoch-based deterministic seed shuffling ($42 + \text{epoch}$). Training loss converged from $1.82 \to 0.0404$. Saved as `spider_checkpoint.pt`.
  - **Total Training Time:** 49 minutes.

---

## 4.5 Comparative Experimental Benchmarks

We evaluated all baseline variants on the complete, held-out Spider validation set (1,034 examples across 20 unseen databases):

| Model / Baseline Configuration | Exact Match (EM) | Execution Accuracy | Invalid SQL Rate |
|---|---:|---:|---:|
| **Deterministic Template Parser** | 0.00% (0/1034) | 5.80% (60/1034) | **0.58%** (6/1034) |
| **Initial LSTM (Job 361487, 10 epochs, raw)** | 0.39% (4/1034) | 1.55% (16/1034) | 85.20% (881/1034) |
| **Optimized Pointer-Gen LSTM (Job 361547, 25 epochs + SQL Repair)** | **3.29% (34/1034)** | **5.90% (61/1034)** | **77.66% (803/1034)** |

### Key Benchmark Takeaways:
1. **Surpasses Deterministic Baseline:** The Optimized LSTM achieves **5.90% Execution Accuracy**, surpassing the Template Baseline (5.80%) while delivering **3.29% Exact Match** (where the template baseline achieved 0.00%).
2. **Alignment with Yale Spider Benchmark Literature:** In the seminal Spider paper (*Yu et al., EMNLP 2018*, Table 4), standard Seq2Seq baselines without schema graphs achieved **3.2% to 5.4% Exact Match**. Our baseline result of **3.29%** aligns directly with this established literature baseline.
3. **8.4$\times$ Exact Match Surge:** Extending Spider training to 25 epochs and applying syntax repair increased exact match from 0.39% to 3.29% (+743% relative improvement).

---

## 4.6 Quantitative Breakdowns

### A. Breakdown by Query Difficulty Tier (Spider Dev)

| Difficulty Tier | Total Examples | Exact Match (EM) | Execution Accuracy | Invalid SQL Rate |
|---|---:|---:|---:|---:|
| **Easy** | 248 | **10.89%** (27/248) | **13.31%** (33/248) | **62.10%** (154/248) |
| **Medium** | 446 | **0.22%** (1/446) | **4.04%** (18/446) | **81.61%** (364/446) |
| **Hard** | 174 | **3.45%** (6/174) | **5.75%** (10/174) | **81.03%** (141/174) |
| **Extra-Hard** | 166 | **0.00%** (0/166) | **0.00%** (0/166) | **86.75%** (144/166) |
| **Overall** | **1,034** | **3.29%** (34/1034) | **5.90%** (61/1034) | **77.66%** (803/1034) |

### B. Breakdown by Query Structure (Spider Dev)

| Query Structure | Total Examples | Exact Match (EM) | Execution Accuracy | Invalid SQL Rate |
|---|---:|---:|---:|---:|
| **Single-Table** | 544 | **5.88%** (32/544) | **9.38%** (51/544) | **71.51%** (389/544) |
| **Multi-Table Join** | 438 | **0.00%** (0/438) | **1.83%** (8/438) | **86.53%** (379/438) |
| **Other (Compound/Subquery)** | 52 | **3.85%** (2/52) | **3.85%** (2/52) | **67.31%** (35/52) |

---

## 4.7 Qualitative Error Analysis & Diagnostic Case Studies

Across the 1,034 validation queries, 803 resulted in SQLite execution errors, 170 executed cleanly but produced incorrect answer rows, 28 achieved execution accuracy via valid alternative formulations, and 33 matched exactly in both SQL text and execution results. Below are representative diagnostic case studies:

### Case Study 1: Disjunctive Filtering and Literal Copying (Full Success)
- **Example ID:** `spider-dev-20` (Difficulty: Medium | Structure: Single-Table)
- **Question:** *"How many concerts are there in year 2014 or 2015?"*
- **Gold SQL:** `SELECT count(*) FROM concert WHERE YEAR = 2014 OR YEAR = 2015`
- **Predicted SQL:** `SELECT COUNT(*) FROM concert WHERE year = 2014 OR year = 2015`
- **Result:** Exact Match = True, Execution Accuracy = True.
- **Diagnostic:** The pointer-generator mechanism successfully copied the numeric tokens `2014` and `2015` directly from the input question into the `WHERE` clause without OOV degradation, correctly capturing the `OR` disjunction.

### Case Study 2: Semantic Equivalence & Punctuation Invariance (Execution Match Only)
- **Example ID:** `spider-dev-87` (Difficulty: Easy | Structure: Single-Table)
- **Question:** *"How many continents are there?"*
- **Gold SQL:** `SELECT count(*) FROM CONTINENTS;`
- **Predicted SQL:** `SELECT COUNT(*) FROM continents`
- **Result:** Exact Match = False, Execution Accuracy = True.
- **Diagnostic:** The gold annotation contained a trailing semicolon `;`. While strict character normalization marked string exact match as False, execution comparison against SQLite verified identical result tables `(5,)`, demonstrating the necessity of execution-based metrics over surface string matching.

### Case Study 3: Projection Omission in Multi-Column Selection
- **Example ID:** `spider-dev-2` (Difficulty: Medium | Structure: Single-Table)
- **Question:** *"Show name, country, age for all singers ordered by age from the oldest to the youngest."*
- **Gold SQL:** `SELECT name , country , age FROM singer ORDER BY age DESC`
- **Predicted SQL:** `SELECT name, country FROM singer ORDER BY age DESC`
- **Result:** Valid SQL, but Execution Accuracy = False.
- **Diagnostic:** The model learned the correct table `singer`, the sorting condition `ORDER BY age DESC`, and the first two projection items (`name, country`), but omitted the third item `age`. This indicates strong grammatical generation, with an attention lapse on lengthy projection lists.

### Case Study 4: Schema Column Hallucination / Semantic Substitution
- **Example ID:** `spider-dev-4` (Difficulty: Medium | Structure: Single-Table)
- **Question:** *"What is the average, minimum, and maximum age of all singers from France?"*
- **Gold SQL:** `SELECT avg(age) , min(age) , max(age) FROM singer WHERE country = 'France'`
- **Predicted SQL:** `SELECT AVG(age), MIN(age), MAX(age) FROM singer WHERE text = 'france'`
- **Result:** Invalid SQL (`sqlite3.OperationalError: no such column: text`).
- **Diagnostic:** The model successfully synthesized complex nested aggregations (`AVG(age), MIN(age), MAX(age)`) and copied the filter value `'france'`. However, it substituted the proper schema column `country` with the generic token `text`. Because `singer` lacks a `text` column, SQLite threw an immediate column error.

### Case Study 5: Multi-Table Join & Relation Hallucination
- **Example ID:** `spider-dev-24` (Difficulty: Extra-Hard | Structure: Multi-Table Join)
- **Question:** *"Show the stadium name and capacity with most number of concerts in year 2014 or after."*
- **Gold SQL:** `SELECT T2.name , T2.capacity FROM concert AS T1 JOIN stadium AS T2 ON T1.stadium_id = T2.stadium_id WHERE T1.year >= 2014 GROUP BY T2.stadium_id ORDER BY count(*) DESC LIMIT 1`
- **Predicted SQL:** `SELECT t2.stadium, t1.Singer_ID, t1.capacity FROM singer_in_concert AS t1 JOIN singer AS t2 ON t1.Singer_ID = t2.concert_ID WHERE t2.year >= 2014 GROUP BY t1.name ORDER BY COUNT(*) DESC LIMIT 1`
- **Result:** Invalid SQL.
- **Diagnostic:** The model synthesized an exceptionally complex SQL clause structure (`JOIN ... ON ... WHERE ... GROUP BY ... ORDER BY ... LIMIT 1`). However, it hallucinated connections across unrelated tables (`singer_in_concert` and `singer` instead of `concert` and `stadium`). Sequential LSTMs lack relational graph inductive bias, preventing them from traversing foreign key graphs reliably.

### Case Study 6: Syntax Repair Impact on WikiSQL
- **WikiSQL Dev Execution:** In initial runs, 99.67% of WikiSQL predictions failed due to unquoted string literals (`WHERE player = John`).
- **Post-Processing Impact:** With `sql_repair.py`, single-table queries are canonicalized, imaginary multi-table joins are pruned, and string literals are automatically enclosed in quotes (`WHERE player = 'John'`). This achieved **100% syntactic validity** across the entire WikiSQL validation set.

---

## 4.8 Limitations & Bridge to Part 3 Roadmap

The quantitative breakdowns and error analyses identify three distinct architectural limitations of classical LSTMs that dictate our Part 3 transformer direction:

| Identified Limitation | Empirical Evidence | Proposed Part 3 Transformer Solution |
|---|---|---|
| **1. Column Hallucination** | 62.1% invalid rate on Easy queries; substituting `country` with `text` (Case 4). | **Cross-Attention Schema Linking:** Pre-trained cross-encoder explicitly scoring question token-to-column alignments before decoding. |
| **2. Foreign-Key Join Hallucination** | Multi-table execution accuracy drops to 1.83% (Case 5). | **Relational Graph Embeddings / RESDSQL:** Encoding schema foreign keys as relational graph edge embeddings (RAT-SQL/T5) or decoupled schema ranking. |
| **3. Syntax & Grammar Invalidity** | 77.66% overall invalid SQL rate due to unconstrained token generation. | **Constrained Grammatical Decoding (PICARD):** Enforcing incremental SQLite AST grammar parsing at each beam decoding step to guarantee 100% syntactically valid SQL. |

---

## References

1. **Bahdanau, D., Cho, K., & Bengio, Y. (2015).** Neural Machine Translation by Jointly Learning to Align and Translate. *ICLR 2015*.
2. **Hochreiter, S., & Schmidhuber, J. (1997).** Long Short-Term Memory. *Neural Computation*, 9(8), 1735–1780.
3. **Li, H., Zhang, J., Li, C., & Chen, H. (2023).** RESDSQL: Decoupling Schema Linking and Skeleton Parsing for Text-to-SQL. *AAAI 2023*.
4. **Popescu, A.-M., Etzioni, O., & Kautz, H. (2003).** Towards a Theory of Natural Language Interfaces to Databases. *IUI 2003*.
5. **Scholak, T., Schucher, N., & Bahdanau, D. (2021).** PICARD: Parsing Incrementally for Constrained Auto-Regressive Decoding from Language Models. *EMNLP 2021*.
6. **See, A., Liu, P. J., & Manning, C. D. (2017).** Get To The Point: Summarization with Pointer-Generator Networks. *ACL 2017*.
7. **Sutskever, I., Vinyals, O., & Le, Q. V. (2014).** Sequence to Sequence Learning with Neural Networks. *NeurIPS 2014*.
8. **Vinyals, O., Fortunato, M., & Jaitly, N. (2015).** Pointer Networks. *NeurIPS 2015*.
9. **Wang, B., Shin, R., Liu, X., Polozov, O., & Richardson, M. (2020).** RAT-SQL: Relation-Aware Schema Encoding and Linking for Text-to-SQL Parsers. *ACL 2020*.
10. **Wong, Y. W., & Mooney, R. J. (2007).** Learning Synchronous Grammars for Semantic Parsing with Lambda Calculus. *ACL 2007*.
11. **Xu, X., Liu, C., & Song, D. (2017).** SQLNet: Generating Structured Queries from Natural Language Without Reinforcement Learning. *arXiv:1711.04436*.
12. **Yu, T., Zhang, R., Yang, K., Yasunaga, M., Wang, D., Li, Z., Ma, J., Li, I., Yao, Q., Roman, S., Zhang, Z., & Radev, D. (2018).** Spider: A Large-Scale Human-Labeled Dataset for Complex and Cross-Domain Semantic Parsing and Text-to-SQL. *EMNLP 2018*.
13. **Zettlemoyer, L. S., & Collins, M. (2005).** Learning to Map Sentences to Logical Form: Structured Classification with Probabilistic Categorial Grammars. *UAI 2005*.
14. **Zhong, V., Xiong, C., & Socher, R. (2017).** Seq2SQL: Generating Structured Queries from Natural Language using Reinforcement Learning. *arXiv:1709.00103*.
