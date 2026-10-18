"""Figure for the Part 3 report: T5-base training curves (HPC job 398846).

Two panels on separate scales (no dual axis): dev execution accuracy per epoch,
and train vs dev loss per epoch. The checkpoint was selected by dev accuracy
(epoch 14), not by dev loss (lowest at epoch 2).

    uv run python -m scripts.plot_t5_training [history.jsonl]
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA = Path(os.environ.get("TEXT2SQL_DATA_ROOT", "/Users/roshini/datasets/text-to-sql"))
HISTORY = DATA / "part3" / "t5-base-ex" / "history.jsonl"
OUT = Path(__file__).resolve().parent.parent / "docs" / "t5_training_curve.png"

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e1"


def _style(ax) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlabel("Epoch", color=MUTED, fontsize=8)


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else HISTORY
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    epochs = [int(r["epoch"]) for r in rows]
    dev_ex = [100 * r["dev_ex"] for r in rows]
    train_loss = [r["train_loss"] for r in rows]
    dev_loss = [r["dev_loss"] for r in rows]
    best = max(range(len(rows)), key=lambda i: dev_ex[i])
    low = min(range(len(rows)), key=lambda i: dev_loss[i])

    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 2.5), facecolor="#fcfcfb")
    for ax in (left, right):
        ax.set_facecolor("#fcfcfb")
        _style(ax)

    left.plot(epochs, dev_ex, color=BLUE, linewidth=2, marker="o", markersize=3)
    left.plot(
        epochs[best],
        dev_ex[best],
        "o",
        color=BLUE,
        markersize=8,
        markeredgecolor="#fcfcfb",
        markeredgewidth=2,
    )
    left.annotate(
        f"chosen: epoch {epochs[best]}, {dev_ex[best]:.1f}%",
        (epochs[best], dev_ex[best]),
        xytext=(0, 9),
        textcoords="offset points",
        fontsize=8,
        color=INK,
        ha="center",
    )
    left.set_ylim(top=max(dev_ex) + 5)
    left.set_title("Dev execution accuracy (%)", fontsize=9, color=INK, loc="left")

    right.plot(epochs, train_loss, color=ORANGE, linewidth=2)
    right.plot(epochs, dev_loss, color=BLUE, linewidth=2)
    right.plot(
        epochs[low],
        dev_loss[low],
        "o",
        color=BLUE,
        markersize=8,
        markeredgecolor="#fcfcfb",
        markeredgewidth=2,
    )
    right.annotate(
        f"lowest dev loss: epoch {epochs[low]}",
        (epochs[low], dev_loss[low]),
        xytext=(8, 14),
        textcoords="offset points",
        fontsize=8,
        color=INK,
    )
    right.text(epochs[-1], dev_loss[-1] + 0.04, "dev", fontsize=8, color=INK, ha="right")
    right.text(epochs[-1], train_loss[-1] + 0.04, "train", fontsize=8, color=INK, ha="right")
    right.set_title("Cross-entropy loss", fontsize=9, color=INK, loc="left")
    right.legend(
        ["train loss", "dev loss"],
        fontsize=7,
        frameon=False,
        loc="center right",
        bbox_to_anchor=(1.0, 0.42),
    )

    fig.tight_layout()
    fig.savefig(OUT, dpi=200)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
