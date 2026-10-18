"""Live T5 training demonstration for the viva, run as a short HPC job.

Fine-tunes t5-small on the Spider *train* questions of a few databases,
printing per-epoch training and held-out loss, then decodes held-out questions
from the same databases and checks each against the gold SQL by execution.

Like the Part 2 LSTM demo this is in-domain (it shows that training works end
to end); the reported cross-domain results come from the full T5-base run.
"""

from __future__ import annotations

import argparse
import logging
import time

from ..config import SPIDER_ROOT
from ..data.contracts import DatasetSplit
from ..data.spider import load_spider
from ..evaluation.metrics import evaluate_predictions
from ..lstm.train_demo import _loss_bar, split_demo_records
from .t5_adapter import T5Baseline, T5Config

GREEN, RED, BOLD, RESET = "\033[32m", "\033[31m", "\033[1m", "\033[0m"


def run(databases: tuple[str, ...], epochs: int, checkpoint: str, show: int) -> int:
    started = time.monotonic()
    records = load_spider(
        SPIDER_ROOT / "train_spider.json",
        SPIDER_ROOT / "tables.json",
        SPIDER_ROOT / "database",
        split=DatasetSplit.TRAIN,
    ).records
    chosen = tuple(r for r in records if r.database_id in databases)
    if not chosen:
        raise ValueError(f"No Spider train questions for databases {databases}")
    train, held_out = split_demo_records(chosen, held_out_fraction=0.2, seed=42)
    print(f"{BOLD}T5 live training demo{RESET}: {checkpoint} on {', '.join(databases)}")
    print(f"  {len(train)} training questions, {len(held_out)} held-out questions\n")

    model = T5Baseline(
        T5Config(checkpoint=checkpoint, epochs=epochs, batch_size=8, learning_rate=5e-4)
    )
    scale = {"value": None}

    def show_epoch(_model, _tokenizer, record):
        scale["value"] = scale["value"] or record["train_loss"]
        bar = _loss_bar(record["train_loss"], scale["value"])
        print(
            f"  epoch {int(record['epoch']):>2}  train {record['train_loss']:.3f}  "
            f"held-out {record['dev_loss']:.3f}  {bar}",
            flush=True,
        )

    model.fit(train, dev_examples=held_out, log_every=0, on_epoch_end=show_epoch)

    predictions = model.predict_records(held_out, num_beams=4)
    report = evaluate_predictions(tuple(held_out), predictions)
    print(f"\n{BOLD}Held-out questions{RESET} (first {show}):")
    for example, prediction, outcome in list(zip(held_out, predictions, report.examples))[:show]:
        ok = outcome.execution_match_official
        verdict = f"{GREEN}CORRECT{RESET}" if ok else f"{RED}WRONG{RESET}"
        print(f"  Q: {example.question}\n     pred: {prediction.predicted_sql}")
        if not ok:
            print(f"     gold: {example.gold_sql}")
        print(f"     {verdict}")
    print(
        f"\n{BOLD}Execution accuracy{RESET} {report.execution_accuracy_official:.1%} "
        f"on {report.evaluated_count} held-out questions; invalid SQL "
        f"{report.invalid_sql_rate:.1%}; total {time.monotonic() - started:.0f}s"
    )
    return 0


def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--databases", default="soccer_2")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--checkpoint", default="google-t5/t5-small")
    parser.add_argument("--show", type=int, default=6)
    args = parser.parse_args()
    return run(tuple(args.databases.split(",")), args.epochs, args.checkpoint, args.show)


if __name__ == "__main__":
    raise SystemExit(main())
