"""Decode Spider with an open-weight GPT model (zero-/few-shot) and write predictions.

python -m scripts.run_gpt --shots 0,3 --split dev --output-dir ART
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from dataclasses import asdict, replace
from pathlib import Path

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")

from scripts.run_ablation import _write, load_records
from scripts.run_t5 import load_train
from text_to_sql.llm.gpt_adapter import GPTBaseline, GPTConfig


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", default="openai/gpt-oss-20b")
    parser.add_argument("--shots", default="0,3")
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--reasoning-effort", default="low")
    parser.add_argument("--max-new-tokens", type=int, default=1024)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    records = load_records("spider", args.split, args.limit)
    pool = load_train(None, include_others=False)
    base = GPTConfig(
        model_id=args.model_id,
        batch_size=args.batch_size,
        reasoning_effort=args.reasoning_effort,
        max_new_tokens=args.max_new_tokens,
    )
    model = GPTBaseline(base).load()
    summary = {}
    for shots in (int(s) for s in args.shots.split(",")):
        runner = GPTBaseline(replace(base, shots=shots), pool, model._model, model._tokenizer)
        started = time.monotonic()
        predictions = runner.predict_records(records)
        out = args.output_dir / f"spider-{args.split}" / runner.name
        report = _write(out, records, predictions)
        summary[runner.name] = {
            "config": asdict(runner.config),
            "n": report.evaluated_count,
            "exec_strict": report.execution_accuracy,
            "exec_official_style": report.execution_accuracy_official,
            "invalid": report.invalid_sql_rate,
            "seconds": round(time.monotonic() - started, 1),
        }
        print(runner.name, summary[runner.name], flush=True)
    (args.output_dir / f"spider-{args.split}" / "summary.json").write_text(
        json.dumps(summary, indent=2)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
