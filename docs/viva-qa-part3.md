# Part 3 Viva Q&A (plain answers)

Short answers you can say out loud. Each one matches a section of `docs/part-3-report.pdf`.
For the demo order and commands, see `docs/viva-day-checklist.md`.

---

## The big picture

**Q: What did you build in Part 3?**
Two modern models and one improvement. (1) T5-base, a pre-trained transformer we fine-tuned on Spider. (2) gpt-oss-20b, a large language model we only prompted, no training. (3) Our novelty: two decoding steps for T5 (A and B) that stop it from using tables and columns that don't exist. A + B raised T5 from 54.1% to 64.4% execution accuracy on Spider dev.

**Q: What does the results table show about how NLP has evolved?**
Rules and LSTMs: under 10%. Fine-tuned pre-trained transformer: 54%. With our decoding: 64%. Instruction-tuned LLM with no training: 79%. Each generation needs less task-specific work and does better.

---

## How the models learn (the weights question)

**Q: How were the LSTM's weights assigned?**
They started as small random numbers. For each training example the model predicted the gold SQL one token at a time. The loss is how unlikely it found the correct token (cross-entropy). Backpropagation works out, for every weight, which direction reduces that loss, and the Adam optimiser nudges each weight a little in that direction. Repeating this over all examples for many epochs gives the trained weights. Nothing was pre-trained.

**Q: How are T5's weights learned? How is that different?**
Same loss and same backpropagation, but T5 does not start random. Google first pre-trained it on a huge web text corpus by hiding chunks of text and making it fill them in, so its weights already encode English and some code. We load those weights and fine-tune all 220 million of them on our 7,000 question → SQL pairs. Because it starts from knowledge, it learns much more from little data. The only new weights are the embeddings for the two tokens we added (`<`, `<=`).

**Q: Were any weights frozen?**
T5: no, all trainable. gpt-oss: all frozen, we never train it; the task is given in the prompt (in-context learning).

**Q: What is self-attention, in one sentence?**
Each token builds its new representation as a weighted average of all other tokens, where the weights say how relevant each other token is. So "singers" in the question can look directly at the column `singer` in the schema, wherever it is.

**Q: Why is a transformer better than the LSTM here?**
The LSTM reads one token at a time and has to carry information through every step; long schemas get lost. Self-attention connects any two tokens directly. And T5 is pre-trained, the LSTM was not.

**Q: What is fine-tuning vs prompting?**
Fine-tuning changes the model's weights using labelled examples (T5). Prompting keeps the weights fixed and puts instructions and examples in the input (gpt-oss).

---

## Data and preprocessing

**Q: What does T5 actually see as input?**
One line: the question, then `|`, the database name, then each table with its columns, then the foreign keys. Example on report page 3.

**Q: What was the `<` problem?**
T5's vocabulary has no `<` symbol, so "age < 30" became "age <unk> 30" and the model could never write "less than". 320 training queries had this. We added `<` and `<=` as new tokens before training.

**Q: What tokenizer does T5 use?**
SentencePiece sub-words, 32,000 pieces. Rare names are split into known pieces (`concert_singer` → `concert _ s inger`), so there are no unknown words, unlike the LSTM's word vocabulary.

**Q: Why no lower-casing, stemming or stop-word removal?**
Table names, values and SQL keywords must be copied exactly; changing them would make the SQL wrong.

**Q: Any data problem you found?**
24% of training inputs are longer than T5's 512-token limit, so the end of big schemas is cut off. And one training query uses a table that doesn't exist.

---

## The novelty (A and B)

**Q: What problem does your novelty solve?**
T5's main error is schema linking: 31% of its queries don't run, mostly "no such column". It uses a column from the wrong table.

**Q: Explain A in simple steps.**
Beam search keeps the 8 best partial queries. (1) Before decoding, make a list of allowed words: SQL keywords, this database's tables and columns, aliases like T1, and the question's words. (2) While decoding, if a beam finishes a word not on the list, throw that beam away. (3) At the end, ask SQLite to compile each finished query with `EXPLAIN`, without running it, and pick the first that compiles.

**Q: Explain B.**
Run the candidate queries in order and keep the first one that runs and returns rows. For the LLM, if its query fails, send it the error message and ask it to fix it, at most twice.

**Q: What is new compared with PICARD?**
PICARD needs a full SQL parser that checks every partial query. Ours only checks completed words against the schema and then uses SQLite itself to judge whole queries. Simpler, works with any model and any SQLite database.

**Q: Does it need retraining?**
No. It only changes how we pick among the model's candidates.

**Q: How do you know it really helps?**
+10.3 points EX on 1,034 dev questions, with a 95% confidence interval of [7.5, 13.3] that never touches zero, and McNemar's test p < 10^-26. It fixed 110 questions and broke 3. EM also went up by 7.4, so the SQL is genuinely better, not just luckier.

**Q: What are its hyperparameters?**
8 beams; check every step; EXPLAIN on finished queries; rerank timeout 5 seconds; 2 retries for the LLM.

**Q: Could A block a correct query?**
We tested it on the gold queries themselves: it rejected 0 of 1,034 dev and 1 of 7,000 training queries, and that one uses a table that doesn't exist.

**Q: What can't it fix?**
Queries that run but answer the wrong question, e.g. the right syntax with the wrong column. Running a query can't tell you it's the wrong meaning.

**Q: Why does B barely help the LLM?**
gpt-oss almost never writes invalid SQL (8 of 1,034), so there is almost nothing for error feedback to fix (+0.1 points).

---

## Metrics and results

**Q: Why execution accuracy?**
It checks the answer, not the wording. Any correct query counts. Weakness: a wrong query can give the right answer by coincidence (our pets_1 "cat aged 3" example).

**Q: Why does gpt-oss have 79% EX but only 20% EM?**
It writes correct SQL in its own style, with aliases like `AS total_singers` or `LEFT JOIN`. Exact match compares structure with Spider's gold query, so it marks those wrong. That's a limitation of exact match, not of the model.

**Q: Why didn't you use BLEU?**
Two queries can share most words and give different answers, or share few and give the same answer. Text overlap doesn't measure correctness.

**Q: How did you choose the T5 checkpoint?**
After every epoch we measured dev execution accuracy and kept the best (epoch 14). Dev loss was lowest at epoch 2, but that model still wrote broken SQL, so loss was a bad guide.

**Q: Isn't choosing on dev cheating?**
It makes dev scores slightly optimistic, which is why the final claims use the test set, run once at the end.

**Q: Where does A + B help most?**
Joins: 25.6% → 39.7% on multi-table questions versus 68.2% → 73.5% on single-table ones. Joins name more tables and columns, so they have more chances to name a wrong one.

---

## Challenges (have two ready)

1. **The `<` token**: found it, added it to the vocabulary.
2. **Loss vs accuracy**: dev loss said epoch 2, accuracy said epoch 14; we switched to accuracy.
3. **gpt-oss on the HPC**: its 4-bit kernels needed C headers the cluster lacks, so we ran it in 16-bit.
4. **Shared GPU out of memory**: smaller batches and splitting the run into halves.
5. **One GPU job per user**: we ran jobs one at a time and keep the queue empty for the viva.
