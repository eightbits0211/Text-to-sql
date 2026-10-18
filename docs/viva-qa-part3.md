# Part 3 Viva Q&A (plain answers)

Short answers you can say out loud. Each one matches a section of `docs/part-3-report.pdf`.
For the demo order and commands, see `docs/viva-day-checklist.md`.

---

## The big picture

**Q: What did you build in Part 3?** *(I did this project alone; say "I", not "we".)*
Two modern models and one improvement. (1) T5-base, a pre-trained transformer I fine-tuned on Spider. (2) gpt-oss-20b, a large language model I only prompted, no training. (3) My novelty: two decoding steps for T5 (A and B) that stop it from using tables and columns that don't exist. A + B raised T5 from 54.1% to 64.4% execution accuracy on Spider dev.

**Q: What does the results table show about how NLP has evolved?**
On the test set: rules 9.5%, LSTM 7.2%, fine-tuned T5-base 53.4%, with my decoding 62.4%, instruction-tuned LLM with three examples and no training 79.3%. Each generation needs less task-specific work and does better.

---

## How the models learn (the weights question)

**Q: How were the LSTM's weights assigned?**
They started as small random numbers. For each training example the model predicted the gold SQL one token at a time. The loss is how unlikely it found the correct token (cross-entropy). Backpropagation works out, for every weight, which direction reduces that loss, and the Adam optimiser nudges each weight a little in that direction. Repeating this over all examples for many epochs gives the trained weights. Nothing was pre-trained.

**Q: How are T5's weights learned? How is that different?**
Same loss and same backpropagation, but T5 does not start random. Google first pre-trained it on a huge web text corpus by hiding chunks of text and making it fill them in, so its weights already encode English and some code. I load those weights and fine-tune all 220 million of them on my 7,000 question → SQL pairs. Because it starts from knowledge, it learns much more from little data. The only new weights are the embeddings for the two tokens I added (`<`, `<=`).

**Q: Were any weights frozen?**
T5: no, all trainable. gpt-oss: all frozen, I never train it; the task is given in the prompt (in-context learning).

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
T5's vocabulary has no `<` symbol, so "age < 30" became "age <unk> 30" and the model could never write "less than". 320 training queries had this. I added `<` and `<=` as new tokens before training.

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
PICARD needs a full SQL parser that checks every partial query. Mine only checks completed words against the schema and then uses SQLite itself to judge whole queries. Simpler, works with any model and any SQLite database.

**Q: Does it need retraining?**
No. It only changes how I pick among the model's candidates.

**Q: How do you know it really helps?**
On the held-out test set (2,147 questions, run once): +9.0 points EX (53.4% → 62.4%), 95% confidence interval [7.3, 10.9] that never touches zero, McNemar p < 10^-50. It fixed 196 questions and broke 3. Dev showed the same (+10.3). EM also rose by 7.1, so the SQL is genuinely better, not just luckier.

**Q: What are its hyperparameters?**
8 beams; check every step; EXPLAIN on finished queries; rerank timeout 5 seconds; 2 retries for the LLM.

**Q: Could A block a correct query?**
I tested it on the gold queries themselves: it rejected 0 of 1,034 dev and 1 of 7,000 training queries, and that one uses a table that doesn't exist.

**Q: What can't it fix?**
Queries that run but answer the wrong question, e.g. the right syntax with the wrong column. Running a query can't tell you it's the wrong meaning.

**Q: Why does B barely help the LLM?**
gpt-oss almost never writes invalid SQL (8 of 1,034), so there is almost nothing for error feedback to fix (+0.1 points).

---

## Metrics and results

**Q: Why execution accuracy?**
It checks the answer, not the wording. Any correct query counts. Weakness: a wrong query can give the right answer by coincidence (my pets_1 "cat aged 3" example).

**Q: Why does gpt-oss have 79% EX but only 37% EM on test?**
It writes correct SQL in its own style, with aliases like `AS total_singers` or `LEFT JOIN`. Exact match compares structure with Spider's gold query, so it marks those wrong. That's a limitation of exact match, not of the model.

**Q: Why didn't you use BLEU?**
Two queries can share most words and give different answers, or share few and give the same answer. Text overlap doesn't measure correctness.

**Q: How did you choose the T5 checkpoint?**
After every epoch I measured dev execution accuracy and kept the best (epoch 14). Dev loss was lowest at epoch 2, but that model still wrote broken SQL, so loss was a bad guide.

**Q: Isn't choosing on dev cheating?**
It makes dev scores slightly optimistic, which is why the final claims use the test set, run once at the end.

**Q: Why only 3-shot gpt-oss on the test set? What about 0-shot?**
I compared 0-shot and 3-shot on dev (78.6% vs 81.2%) and only ran the winner on test. Running every variant on test and then picking the best would be choosing on the test set, which inflates the result. The 0-shot numbers are in the small prompt-settings table as a dev ablation, like A and B for T5.

**Q: Where does A + B help most?**
Joins: 25.6% → 39.7% on multi-table questions versus 68.2% → 73.5% on single-table ones. Joins name more tables and columns, so they have more chances to name a wrong one.

---

**Q: Explain the training-curve figure.**
Left: dev execution accuracy after each epoch; it climbs fast, then levels off around 48–51%, best at epoch 14. Right: training loss keeps falling, but dev loss is lowest at epoch 2 and then rises. Rising dev loss means the model is becoming over-confident on the tokens it gets wrong, yet it still gets more whole queries right. That's why I chose the checkpoint by accuracy, not loss.

**Q: What does the outcome-by-difficulty table show?**
Each test question is correct, ran-but-wrong, or invalid. A + B halves the invalid ones (662 → 328). Of the 334 it rescues, 193 become correct and 141 run but give the wrong answer. So my method fixes "doesn't run" errors; what's left is mostly "wrong meaning".

---

## Challenges (have three ready; report §e has all twelve)

Tell each as: what happened, how I noticed, what I did, what changed.

1. **WikiSQL scoring bug (Part 2).** Gold queries used column names the database didn't have, so SQLite read them as text constants and 6,007 of 8,415 returned nothing. Empty predictions were being counted correct. I noticed by checking that gold answers are real, fixed it with a view that renames the columns, and recomputed every WikiSQL score.
2. **The LSTM memorised.** Training loss went to 0.04 but dev loss rose and 72% of dev queries didn't run. That's why I moved to a pre-trained transformer: 7.2% → 53.4% on test.
3. **Loss vs accuracy.** Dev loss said epoch 2 was best, but that model wrote broken SQL. Choosing by dev accuracy instead (epoch 14) took greedy dev accuracy from 41.6% to 53.8%, same training run.
4. **The `<` token.** T5 couldn't write "less than"; 320 training queries affected. I added the token.
5. **Inventing columns.** 275 of T5's 317 invalid dev queries were "no such column". That's the problem my novelty solves: invalid test queries 662 → 328.
6. **Test-run crash.** One test database had a foreign key with no column named; the job crashed after 515 questions. Fixed, added a test, reran only that half.
7. **Honest limit:** 24% of training schemas are longer than T5's 512-token input, so the end gets cut off. Not solved; schema ranking would fix it.
