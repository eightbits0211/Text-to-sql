"""Build the gpt-oss-20b answer file the CLI demo reads (run on the HPC).

gpt-oss-20b needs ~42 GB of GPU memory, so the laptop demo shows answers
computed here: every Spider dev prediction from an existing run, plus fresh
answers for the scripted demo questions and any extra viva questions.

    python -m scripts.precompute_gpt_answers \
        --dev-predictions ART/gpt-oss-20b-0shot/spider-dev/gpt-0shot-fix2/predictions.jsonl \
        --questions viva_questions.tsv --output ART/gpt_answers.json

``--questions`` is a TSV of ``database_id<TAB>question`` lines (Spider dev databases).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")

from text_to_sql.cli import SCRIPTED_DEMO_CASES, gpt_answer_key
from text_to_sql.config import SPIDER_ROOT
from text_to_sql.data.contracts import DatasetSplit, ExampleRecord, QueryDifficulty, QueryStructure
from text_to_sql.llm.gpt_adapter import GPTBaseline, GPTConfig
from text_to_sql.llm.prompts import extract_sql


def _record(database_id: str, question: str, index: int) -> ExampleRecord:
    path = SPIDER_ROOT / "database" / database_id / f"{database_id}.sqlite"
    if not path.is_file():
        raise FileNotFoundError(f"No Spider database {database_id} at {path}")
    return ExampleRecord(
        example_id=f"demo-{index}",
        dataset="demo",
        split=DatasetSplit.DEV,
        database_id=database_id,
        database_path=path,
        question=question,
        schema_text="(unused by the GPT prompt)",
        gold_sql="SELECT 1",  # unused; required by the record contract
        difficulty=QueryDifficulty.UNKNOWN,
        query_structure=QueryStructure.OTHER,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev-predictions", type=Path, required=True)
    parser.add_argument("--questions", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    answers: dict[str, str] = {}
    for line in args.dev_predictions.read_text().splitlines():
        row = json.loads(line)
        answers[gpt_answer_key(row["database_id"], row["question"])] = row["predicted_sql"]
    print(f"{len(answers)} dev answers")

    asked = [("concert_singer", case.question) for case in SCRIPTED_DEMO_CASES]
    if args.questions is not None:
        for line in args.questions.read_text().splitlines():
            if line.strip():
                database_id, question = line.split("\t", 1)
                asked.append((database_id.strip(), question.strip()))
    records = [_record(db, q, i) for i, (db, q) in enumerate(asked)]

    model = GPTBaseline(GPTConfig(dequantize=True, batch_size=4)).load()
    responses = model.generate([model.messages_for(r) for r in records])
    for record, response in zip(records, responses, strict=True):
        sql = extract_sql(response)
        answers[gpt_answer_key(record.database_id, record.question)] = sql
        print(f"{record.database_id} | {record.question}\n    {sql}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(answers, indent=1, sort_keys=True))
    print(f"wrote {len(answers)} answers to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
