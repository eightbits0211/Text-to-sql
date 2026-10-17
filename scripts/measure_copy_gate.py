"""Measure the pointer-generator copy gate on Spider dev (teacher-forced).

For a seeded sample of dev questions, records p_gen at every gold target
position, split by whether the gold token is in the fixed vocabulary or can
only be produced by copying from the input, plus the probability the model
assigns to the gold token. Tests whether the copy path is used at all.

Usage:
    uv run python -m scripts.measure_copy_gate [--sample 200]
"""

import argparse
import json
import random
import statistics
from pathlib import Path

import torch

from text_to_sql.config import LSTM_CHECKPOINT_DIR, SPIDER_ROOT
from text_to_sql.data.contracts import DatasetSplit
from text_to_sql.data.spider import load_spider
from text_to_sql.lstm import LSTMBaseline
from text_to_sql.lstm.collation import collate_batch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=200)
    parser.add_argument(
        "--checkpoint", type=Path, default=LSTM_CHECKPOINT_DIR / "spider_checkpoint.pt"
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    records = load_spider(
        SPIDER_ROOT / "dev.json",
        SPIDER_ROOT / "tables.json",
        SPIDER_ROOT / "database",
        split=DatasetSplit.DEV,
    ).records
    records = random.Random(42).sample(list(records), min(args.sample, len(records)))
    baseline = LSTMBaseline.from_checkpoint(args.checkpoint)
    model, vocab = baseline._model, baseline._vocabulary
    unk = vocab.token_to_index["<unk>"]
    decoder = model.decoder
    original = decoder.compute_output_distribution
    captured: list[torch.Tensor] = []

    def recording(combined, embedded, attn, extended_size, src_indices):
        gate = torch.sigmoid(decoder.W_gen(torch.cat([combined, embedded], dim=-1)))
        captured.append(gate.squeeze(-1))
        return original(combined, embedded, attn, extended_size, src_indices)

    decoder.compute_output_distribution = recording
    gates: dict[str, list[float]] = {"vocab_target": [], "copy_only_target": []}
    gold_probability: dict[str, list[float]] = {"vocab_target": [], "copy_only_target": []}
    with torch.no_grad():
        for record in records:
            captured.clear()
            batch = collate_batch([record], vocab, torch.device("cpu"))
            output = model.forward(
                batch.src,
                batch.src_lengths,
                batch.tgt,
                batch.tgt_lengths,
                batch.src_token_indices,
                batch.extended_vocab_size,
                1.0,
                unk_index=unk,
            )
            for step, index in enumerate(batch.tgt[0, 1:].tolist()):
                if index == 0:
                    break
                if index == unk:
                    continue
                key = "copy_only_target" if index >= len(vocab) else "vocab_target"
                gates[key].append(captured[step][0].item())
                gold_probability[key].append(output[0, step, index].item())
    summary = {
        key: {
            "n": len(values),
            "mean_p_gen": statistics.mean(values),
            "median_p_gen": statistics.median(values),
            "share_copy_mode": sum(v < 0.5 for v in values) / len(values),
            "mean_gold_probability": statistics.mean(gold_probability[key]),
        }
        for key, values in gates.items()
    }
    print(json.dumps(summary, indent=2))
    if args.output:
        args.output.write_text(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
