# PRD Authority Audit

**Audit date:** 2026-09-21  
**Sources checked:**

- `(2026) CS F429 Project Description and Evaluation.pdf`
- `NLPpart1.pdf`
- [`text-to-sql-prd.md`](./text-to-sql-prd.md)

## Result

The PRD is aligned with the authoritative PDFs after one clarification made on
2026-09-21: Spider's hidden official test labels must not be treated as
available. The PRD now requires the official development split and only a
permitted held-out/test split whose availability and policy are documented.

## Traceability

| Authoritative requirement | PRD coverage | Status |
|---|---|---|
| Dataset selection and justification | Spider, WikiSQL, optional BIRD, limitations, preprocessing, and record contract | Covered |
| Classical versus modern comparison | Classical parser plus T5/BERT-based modern model | Covered |
| Model architecture and training details | Checkpoint, tokenizer, sequence limits, hyperparameters, decoding, hardware, and software requirements | Covered |
| Appropriate evaluation metrics | Exact match, execution accuracy, invalid-SQL rate, limitations, and failure handling | Covered |
| Quantitative and qualitative error analysis | Difficulty, query structure, error categories, examples, and false-positive discussion | Covered |
| Novel contribution | Constrained decoding or execution-error self-correction, ablation, and measurable improvement | Covered |
| Part 2 baseline and demo | Classical baseline, evaluation harness, report evidence, and CLI/GUI flow | Covered |
| Part 3 completion | Modern model, novelty, comparative results, challenges, and final demo | Covered |
| 6–10 page structured report | Report requirement and required evidence are included | Covered |
| Official deadlines | Part 2 and Part 3 deadlines are recorded in project planning documents | Covered |

## Clarifications and boundaries

1. The course PDF allows any NLP problem; the proposal selects Text-to-SQL.
2. WikiSQL is a de-risking warm-up, not a replacement for Spider.
3. BIRD remains optional, matching the proposal.
4. The Part 2 plan intentionally defers the modern model and novelty while
   preserving interfaces for Part 3.
5. The PRD's architecture and exact module names are implementation guidance,
   not additional course requirements.
6. The PRD's invalid-SQL handling strengthens reproducibility and does not
   conflict with the rubric.

## Remaining implementation decisions

These are not authority conflicts and should be resolved through smoke tests:

- Template/grammar baseline versus LSTM.
- Exact modern checkpoint.
- Exact SQL normalization and result-table comparison.
- CLI versus optional web wrapper.
- Constrained decoding versus execution-error self-correction.
