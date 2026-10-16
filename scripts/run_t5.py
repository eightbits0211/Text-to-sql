"""Fine-tune T5 on Spider train and decode Spider dev/test (Part 3 modern baseline).

Training keeps the checkpoint with the lowest dev loss. Decoding writes one
``predictions.jsonl`` per variant in the same format as ``run_ablation.py``, so
official scoring (``run_official_spider_eval.py``) runs afterwards, locally.

    python -m scripts.run_t5 --train --output-dir ART --checkpoint google-t5/t5-base
    python -m scripts.run_t5 --model-dir ART/best --split test --output-dir ART/decode
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from dataclasses import asdict
from pathlib import Path

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")

from scripts.run_ablation import _SPIDER, _write, load_records
from text_to_sql.data.contracts import DatasetSplit
from text_to_sql.data.spider import load_spider
from text_to_sql.evaluation.metrics import Prediction
from text_to_sql.transformer.t5_adapter import T5Baseline, T5Config

LOGGER = logging.getLogger("run_t5")


def load_train(limit: int | None, include_others: bool):
    records = list(
        load_spider(
            _SPIDER / "train_spider.json",
            _SPIDER / "tables.json",
            _SPIDER / "database",
            split=DatasetSplit.TRAIN,
            smoke_limit=limit,
        ).records
    )
    others = _SPIDER / "train_others.json"
    if include_others and others.is_file():
        records += load_spider(
            others, _SPIDER / "tables.json", _SPIDER / "database", split=DatasetSplit.TRAIN
        ).records
    return tuple(records)


def train(args: argparse.Namespace) -> Path:
    config = T5Config(
        checkpoint=args.checkpoint,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        epochs=args.epochs,
        seed=args.seed,
    )
    train_records = load_train(args.train_limit, args.include_others)
    dev_records = load_records("spider", "dev", args.dev_limit)
    print(f"train={len(train_records)} dev={len(dev_records)} config={asdict(config)}", flush=True)

    best_dir = args.output_dir / "best"
    state = {"best": float("inf")}
    history_path = args.output_dir / "history.jsonl"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    history_path.write_text("")
    baseline = T5Baseline(config)

    def on_epoch_end(model, tokenizer, record):
        with history_path.open("a") as handle:
            handle.write(json.dumps(record) + "\n")
        if record.get("dev_loss", float("inf")) < state["best"]:
            state["best"] = record["dev_loss"]
            baseline._model, baseline._tokenizer = model, tokenizer
            baseline.save(best_dir)
            print(f"  saved best (dev_loss={record['dev_loss']:.4f}) to {best_dir}", flush=True)

    baseline.fit(train_records, dev_examples=dev_records, on_epoch_end=on_epoch_end)
    return best_dir


def decode(model_dir: Path, split: str, beams: list[int], limit: int | None, out: Path) -> None:
    baseline = T5Baseline.from_checkpoint(model_dir)
    records = load_records("spider", split, limit)
    summary = {}
    for num_beams in beams:
        started = time.monotonic()
        predictions = baseline.predict_records(records, num_beams=num_beams)
        name = "greedy" if num_beams == 1 else f"beam{num_beams}"
        report = _write(out / f"spider-{split}" / name, records, predictions)
        summary[name] = {
            "n": report.evaluated_count,
            "exec_strict": report.execution_accuracy,
            "exec_official_style": report.execution_accuracy_official,
            "invalid": report.invalid_sql_rate,
            "seconds": round(time.monotonic() - started, 1),
        }
        print(f"{split} {name}: {summary[name]}", flush=True)
    (out / f"spider-{split}" / "summary.json").write_text(json.dumps(summary, indent=2))


def decode_novelty(model_dir: Path, split: str, k: int, limit: int | None, out: Path) -> None:
    """Ablation variants from one k-beam pass without and one with the schema constraint.

    - ``beam``: top unconstrained beam (plain T5)
    - ``A_prune``: top constrained beam
    - ``A_full``: first constrained beam that passes SQLite EXPLAIN
    - ``B_rerank``: execution rerank of the unconstrained beams
    - ``AB``: execution rerank of the constrained beams
    """
    from transformers import LogitsProcessorList

    from text_to_sql.generation.exec_correction import execution_rerank
    from text_to_sql.transformer.constrained import SchemaConstraintProcessor, first_valid

    baseline = T5Baseline.from_checkpoint(model_dir)
    records = load_records("spider", split, limit)
    variants = ("beam", "A_prune", "A_full", "B_rerank", "AB")
    chosen: dict[str, list[Prediction]] = {name: [] for name in variants}
    root = out / f"spider-{split}" / f"novelty-k{k}"
    root.mkdir(parents=True, exist_ok=True)
    started, pruned = time.monotonic(), 0
    with (root / "candidates.jsonl").open("w") as log:
        for index, ex in enumerate(records, start=1):
            plain = baseline.generate_candidates(ex.question, ex.schema_text, k, k)
            processor = SchemaConstraintProcessor(baseline._tokenizer, ex.schema_text, ex.question)
            constrained = baseline.generate_candidates(
                ex.question, ex.schema_text, k, k, LogitsProcessorList([processor])
            )
            pruned += processor.pruned
            picks = {
                "beam": plain[0],
                "A_prune": constrained[0],
                "A_full": first_valid(constrained, ex.database_path),
                "B_rerank": execution_rerank(plain, ex.database_path, ex.execution_prelude).sql,
                "AB": execution_rerank(constrained, ex.database_path, ex.execution_prelude).sql,
            }
            for name, sql in picks.items():
                chosen[name].append(Prediction(ex.example_id, f"t5-{name}", sql))
            log.write(
                json.dumps(
                    {"example_id": ex.example_id, "plain": plain, "constrained": constrained}
                )
                + "\n"
            )
            if index % 100 == 0:
                print(f"  {index}/{len(records)} ({time.monotonic() - started:.0f}s)", flush=True)
    summary = {"k": k, "beams_pruned": pruned, "seconds": round(time.monotonic() - started, 1)}
    for name in variants:
        report = _write(root / name, records, tuple(chosen[name]))
        summary[name] = {
            "n": report.evaluated_count,
            "exec_strict": report.execution_accuracy,
            "exec_official_style": report.execution_accuracy_official,
            "invalid": report.invalid_sql_rate,
        }
        print(f"{split} {name}: {summary[name]}", flush=True)
    (root / "summary.json").write_text(json.dumps(summary, indent=2))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--model-dir", type=Path, help="Decode only, from this checkpoint")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--checkpoint", default="google-t5/t5-base")
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--grad-accum", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-limit", type=int, default=None)
    parser.add_argument("--dev-limit", type=int, default=None)
    parser.add_argument("--include-others", action="store_true")
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--beams", default="1,4")
    parser.add_argument("--novelty-k", type=int, default=0, help="Also run the A/B ablation")
    args = parser.parse_args()

    if not args.train and args.model_dir is None:
        parser.error("pass --train or --model-dir")
    model_dir = train(args) if args.train else args.model_dir
    limit = args.dev_limit if args.split == "dev" else None
    if args.beams:
        beams = [int(b) for b in args.beams.split(",")]
        decode(model_dir, args.split, beams, limit, args.output_dir / "decode")
    if args.novelty_k:
        decode_novelty(model_dir, args.split, args.novelty_k, limit, args.output_dir / "decode")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
