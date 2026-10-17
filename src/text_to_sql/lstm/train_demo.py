"""Live, CPU-sized training demonstration for the viva.

Trains a small pointer-generator LSTM from scratch on all Spider *train*
questions of a few databases, prints the per-epoch training and held-out NLL,
then decodes held-out questions from the same databases and executes them.

This is an in-domain demonstration that training works end to end (Spider
pairs many questions with a paraphrase of the same query, so held-out
questions are close to training ones). The reported cross-domain results come
from the full two-stage HPC run, not from this demo model.
"""

from __future__ import annotations

import random
import time
from pathlib import Path

from ..config import SPIDER_ROOT
from ..data.contracts import DatasetSplit, ExampleRecord
from ..data.spider import load_spider
from ..evaluation.metrics import evaluate_predictions, execute_read_only
from .adapter import LSTMBaseline
from .training import TrainingConfig

DEFAULT_DATABASES = ("soccer_2",)
DEFAULT_SPIDER_ROOT = SPIDER_ROOT
DEFAULT_OUTPUT = Path("artifacts/train-demo")


def split_demo_records(
    records: tuple[ExampleRecord, ...], held_out_fraction: float, seed: int
) -> tuple[list[ExampleRecord], list[ExampleRecord]]:
    """Deterministic per-database train/held-out split."""
    rng = random.Random(seed)
    train: list[ExampleRecord] = []
    held_out: list[ExampleRecord] = []
    by_database: dict[str, list[ExampleRecord]] = {}
    for record in records:
        by_database.setdefault(record.database_id, []).append(record)
    for database_id in sorted(by_database):
        items = list(by_database[database_id])
        rng.shuffle(items)
        cut = max(1, round(len(items) * held_out_fraction))
        held_out.extend(items[:cut])
        train.extend(items[cut:])
    return train, held_out


def _loss_bar(value: float, scale: float, width: int = 40) -> str:
    filled = max(1, min(width, round(width * value / scale))) if scale > 0 else 1
    return "#" * filled


def run_training_demo(
    *,
    spider_root: Path = DEFAULT_SPIDER_ROOT,
    databases: tuple[str, ...] = DEFAULT_DATABASES,
    epochs: int = 60,
    output_dir: Path = DEFAULT_OUTPUT,
    held_out_fraction: float = 0.1,
    show_examples: int = 5,
    seed: int = 42,
) -> int:
    loaded = load_spider(
        spider_root / "train_spider.json",
        spider_root / "tables.json",
        spider_root / "database",
        split=DatasetSplit.TRAIN,
    )
    records = tuple(r for r in loaded.records if r.database_id in set(databases))
    if not records:
        print(f"No Spider train questions found for databases {databases}.")
        return 1
    train, held_out = split_demo_records(records, held_out_fraction, seed)

    print("=" * 70)
    print("  LIVE TRAINING DEMO: pointer-generator LSTM trained from scratch (CPU)")
    print(f"  Databases : {', '.join(databases)}")
    print(f"  Questions : {len(train)} train / {len(held_out)} held out (same databases)")
    print(f"  Epochs    : {epochs} | model: emb 128, hidden 256 (full model: emb 256, hidden 512)")
    print("=" * 70)

    config = TrainingConfig(
        embedding_dim=128,
        hidden_dim=256,
        batch_size=16,
        learning_rate=2e-3,
        max_epochs=0,
        smoke_limit=None,
        seed=seed,
    )
    probe = min((r for r in train if r.database_id == databases[0]), key=lambda r: len(r.gold_sql))
    untrained = LSTMBaseline(config).fit(
        (), checkpoint_dir=output_dir / "untrained", spider_examples=tuple(train), spider_epochs=0
    )
    print(f'\nProbe question (from the training set): "{probe.question}"')
    print(f"  gold SQL                : {probe.gold_sql}")
    before = untrained.predict(probe.question, probe.schema_text)
    print(f"  BEFORE training (random): {before[:90]}{' ...' if len(before) > 90 else ''}\n")

    baseline = LSTMBaseline(config)
    started = time.time()
    baseline.fit(
        (),
        checkpoint_dir=output_dir,
        spider_examples=tuple(train),
        spider_epochs=epochs,
        spider_dev_examples=tuple(held_out),
    )
    elapsed = time.time() - started

    import json

    meta = json.loads((output_dir / "training_meta.json").read_text(encoding="utf-8"))
    train_losses = meta["epoch_losses"]
    dev_losses = meta["spider_dev_losses"]
    scale = max(train_losses + dev_losses)
    print(f"\nTraining finished in {elapsed:.0f}s. Loss curve (NLL per target token):")
    print(f"{'epoch':>5}  {'train':>7}  {'held-out':>8}")
    for epoch, (train_loss, dev_loss) in enumerate(zip(train_losses, dev_losses, strict=True), 1):
        print(f"{epoch:>5}  {train_loss:7.3f}  {dev_loss:8.3f}  {_loss_bar(train_loss, scale)}")

    print(f"\n  AFTER training          : {baseline.predict(probe.question, probe.schema_text)}")

    seen = random.Random(seed).sample(train, min(20, len(train)))
    seen_report = evaluate_predictions(tuple(seen), baseline.predict_records(seen))
    predictions = baseline.predict_records(held_out)
    report = evaluate_predictions(tuple(held_out), predictions)
    print(
        "\nExecution accuracy on 20 questions it trained on : "
        f"{sum(i.execution_match for i in seen_report.examples)}/{len(seen)}"
    )
    print(
        "Execution accuracy on held-out questions         : "
        f"{sum(i.execution_match for i in report.examples)}/{len(held_out)} "
        f"(invalid SQL {report.invalid_sql_rate:.0%})"
    )
    print(
        "  The gap between the two lines is the memorisation-vs-generalisation gap that the\n"
        "  full HPC model also shows on Spider dev/test (report section 4.3)."
    )

    rows = list(zip(held_out, predictions, report.examples, strict=True))
    rows.sort(key=lambda row: (not row[2].execution_match, row[2].invalid_sql))
    print(f"\nSample held-out questions ({show_examples}, correct ones first):")
    for record, prediction, item in rows[:show_examples]:
        result = execute_read_only(
            prediction.predicted_sql, record.database_path, record.execution_prelude
        )
        status = "CORRECT" if item.execution_match else ("INVALID" if item.invalid_sql else "WRONG")
        preview = result.rows[:3] if result.status == "success" else result.error
        print(f"\n  [{status}] ({record.database_id}) {record.question}")
        print(f"    predicted: {prediction.predicted_sql}")
        print(f"    gold     : {record.gold_sql}")
        print(f"    result   : {preview}")

    checkpoint = output_dir / "spider_checkpoint.pt"
    example_db = spider_root / "database" / databases[0] / f"{databases[0]}.sqlite"
    print("\n" + "=" * 70)
    print(f"  Checkpoint saved: {checkpoint}")
    print("  Ask the freshly trained model your own question:")
    print(
        f"    uv run text-to-sql-demo --model lstm --checkpoint {checkpoint} "
        f'--database {example_db} --question "{probe.question}"'
    )
    print("=" * 70)
    return 0
