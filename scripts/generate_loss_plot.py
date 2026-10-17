"""Generate training loss curve figure for the Part 2 report.

Reads epoch losses from the HPC training metadata and produces a two-panel
plot showing Stage 1 (WikiSQL) and Stage 2 (Spider) convergence.

Usage:
    uv run python scripts/generate_loss_plot.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import ticker

# Actual epoch losses from HPC Job 361547
TRAINING_META = Path(
    "/Users/roshini/datasets/text-to-sql/artifacts-lstm-gpu-run/lstm-checkpoint/training_meta.json"
)

OUTPUT_DIR = Path("/Users/roshini/NLPproject/docs")

# training_meta.json files from the multi-seed replication runs
# (scripts/hpc_run_lstm_seed.sh), which also log per-epoch Spider-dev NLL.
SEED_META_GLOB = "/Users/roshini/datasets/text-to-sql/artifacts-seeds/seed-*/training_meta.json"


def main() -> None:
    if TRAINING_META.is_file():
        meta = json.loads(TRAINING_META.read_text(encoding="utf-8"))
        epoch_losses = meta["epoch_losses"]
    else:
        # Hardcoded from HPC Job 361547 training_meta.json as fallback
        epoch_losses = [
            # Stage 1: WikiSQL warm-up (10 epochs)
            1.7228,
            1.0568,
            0.6802,
            0.3785,
            0.2431,
            0.1923,
            0.1599,
            0.1344,
            0.1140,
            0.0976,
            # Stage 2: Spider primary (25 epochs)
            1.8410,
            0.6918,
            0.5377,
            0.4434,
            0.3684,
            0.3088,
            0.2532,
            0.2084,
            0.1727,
            0.1455,
            0.1258,
            0.1069,
            0.0918,
            0.0795,
            0.0693,
            0.0611,
            0.0576,
            0.0554,
            0.0531,
            0.0505,
            0.0478,
            0.0445,
            0.0401,
            0.0399,
            0.0404,
        ]

    wikisql_losses = epoch_losses[:10]
    spider_losses = epoch_losses[10:]

    # --- Plot ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2), sharey=False)
    fig.patch.set_facecolor("white")

    # Color scheme
    wiki_color = "#2563EB"  # blue
    spider_color = "#DC2626"  # red

    # Stage 1: WikiSQL
    epochs_w = list(range(1, len(wikisql_losses) + 1))
    ax1.plot(
        epochs_w,
        wikisql_losses,
        "o-",
        color=wiki_color,
        linewidth=2,
        markersize=5,
        markerfacecolor="white",
        markeredgewidth=1.5,
        label="WikiSQL Warm-up",
    )
    ax1.set_xlabel("Epoch", fontsize=11)
    ax1.set_ylabel("Training Loss (NLL)", fontsize=11)
    ax1.set_title(
        "Stage 1: WikiSQL Warm-up\n(55,968 examples, 10 epochs)", fontsize=11, fontweight="bold"
    )
    ax1.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax1.set_ylim(bottom=0)
    ax1.grid(True, alpha=0.3)
    ax1.annotate(
        f"{wikisql_losses[0]:.2f}",
        xy=(1, wikisql_losses[0]),
        xytext=(1.4, wikisql_losses[0] - 0.05),
        fontsize=8,
        color=wiki_color,
    )
    ax1.annotate(
        f"{wikisql_losses[-1]:.2f}",
        xy=(10, wikisql_losses[-1]),
        xytext=(7.5, wikisql_losses[-1] + 0.15),
        fontsize=8,
        color=wiki_color,
    )

    # Stage 2: Spider
    epochs_s = list(range(1, len(spider_losses) + 1))
    ax2.plot(
        epochs_s,
        spider_losses,
        "s-",
        color=spider_color,
        linewidth=2,
        markersize=4,
        markerfacecolor="white",
        markeredgewidth=1.5,
        label="Spider train NLL (Job 361547)",
    )
    import glob

    dev_colors = ("#7C3AED", "#059669", "#D97706")
    for color, meta_path in zip(dev_colors, sorted(glob.glob(SEED_META_GLOB)), strict=False):
        seed_meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
        dev_losses = seed_meta.get("spider_dev_losses") or []
        if not dev_losses:
            continue
        seed = seed_meta["config"]["seed"]
        ax2.plot(
            range(1, len(dev_losses) + 1),
            dev_losses,
            "--",
            color=color,
            linewidth=1.6,
            label=f"Spider dev NLL (seed {seed})",
        )
        best = min(range(len(dev_losses)), key=dev_losses.__getitem__)
        ax2.plot(best + 1, dev_losses[best], "v", color=color, markersize=7)
    ax2.legend(fontsize=8, loc="center right")
    ax2.set_xlabel("Epoch", fontsize=11)
    ax2.set_ylabel("NLL", fontsize=11)
    ax2.set_title(
        "Stage 2: Spider Primary Training\n(7,000 examples, 25 epochs)",
        fontsize=11,
        fontweight="bold",
    )
    ax2.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax2.set_ylim(bottom=0)
    ax2.grid(True, alpha=0.3)
    ax2.annotate(
        f"{spider_losses[0]:.2f}",
        xy=(1, spider_losses[0]),
        xytext=(3, spider_losses[0] + 0.05),
        fontsize=8,
        color=spider_color,
    )
    ax2.annotate(
        f"{spider_losses[-1]:.4f}",
        xy=(25, spider_losses[-1]),
        xytext=(17, spider_losses[-1] + 0.2),
        fontsize=8,
        color=spider_color,
    )

    # Vertical dashed line showing transition
    fig.text(
        0.5,
        0.02,
        "Solid: training NLL, Job 361547. Dashed: teacher-forced Spider-dev NLL from the "
        "replication runs (triangle = minimum).",
        ha="center",
        fontsize=9,
        fontstyle="italic",
        color="#6B7280",
    )

    plt.tight_layout(rect=[0, 0.06, 1, 1])

    # Save PDF for LaTeX and PNG for markdown
    pdf_path = OUTPUT_DIR / "training_loss_curve.pdf"
    png_path = OUTPUT_DIR / "training_loss_curve.png"
    fig.savefig(pdf_path, dpi=300, bbox_inches="tight")
    fig.savefig(png_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"  Saved PDF: {pdf_path}")
    print(f"  Saved PNG: {png_path}")


if __name__ == "__main__":
    main()
