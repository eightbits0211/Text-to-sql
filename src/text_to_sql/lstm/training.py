"""Bounded CPU smoke training loop for the LSTM seq2seq baseline.

Implements teacher-forced NLL training on a capped slice of examples,
checkpointing, and checkpoint reload verification.
"""

from __future__ import annotations

import json
import math
import os
import random
from dataclasses import dataclass
from pathlib import Path

# Disable experimental PyTorch 2.14+ Triton native JIT ops that require system C headers
os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")

import torch
from torch import nn

from ..data.contracts import ExampleRecord
from .collation import collate_batch
from .model import Seq2SeqLSTM
from .preprocessing import FixedVocabulary, build_training_vocabulary

EPS = 1e-9


@dataclass
class TrainingConfig:
    """Hyperparameters for the LSTM smoke training run."""

    embedding_dim: int = 256
    hidden_dim: int = 512
    num_encoder_layers: int = 2
    num_decoder_layers: int = 2
    dropout: float = 0.2
    learning_rate: float = 1e-3
    grad_clip: float = 1.0
    batch_size: int = 8
    max_epochs: int = 10
    teacher_forcing_ratio: float = 1.0
    max_vocab_size: int | None = None
    smoke_limit: int | None = 200
    seed: int = 42

    def to_dict(self) -> dict[str, object]:
        return {
            "embedding_dim": self.embedding_dim,
            "hidden_dim": self.hidden_dim,
            "num_encoder_layers": self.num_encoder_layers,
            "num_decoder_layers": self.num_decoder_layers,
            "dropout": self.dropout,
            "learning_rate": self.learning_rate,
            "grad_clip": self.grad_clip,
            "batch_size": self.batch_size,
            "max_epochs": self.max_epochs,
            "teacher_forcing_ratio": self.teacher_forcing_ratio,
            "max_vocab_size": self.max_vocab_size,
            "smoke_limit": self.smoke_limit,
            "seed": self.seed,
        }


@dataclass
class TrainingResult:
    """Summary of a completed smoke training run."""

    final_loss: float
    epoch_losses: list[float]
    vocab_size: int
    checkpoint_path: Path
    config: TrainingConfig


def _make_model(vocab_size: int, config: TrainingConfig, device: torch.device) -> Seq2SeqLSTM:
    return Seq2SeqLSTM(
        vocab_size=vocab_size,
        embedding_dim=config.embedding_dim,
        hidden_dim=config.hidden_dim,
        num_encoder_layers=config.num_encoder_layers,
        num_decoder_layers=config.num_decoder_layers,
        dropout=config.dropout,
        padding_idx=0,
    ).to(device)


def _compute_batch_loss(
    model: Seq2SeqLSTM,
    batch: object,
    device: torch.device,
    teacher_forcing_ratio: float,
) -> torch.Tensor:
    """NLL over non-padding target positions, averaged per token."""
    output = model.forward(
        src=batch.src,
        src_lengths=batch.src_lengths,
        tgt=batch.tgt,
        tgt_lengths=batch.tgt_lengths,
        src_token_indices=batch.src_token_indices,
        extended_vocab_size=batch.extended_vocab_size,
        teacher_forcing_ratio=teacher_forcing_ratio,
    )
    # output: (batch, tgt_len-1, extended_vocab_size)
    # target: tgt[:, 1:]
    target = batch.tgt[:, 1:].contiguous()
    mask = ~batch.tgt_mask  # True where real token
    log_probs = torch.log(output.clamp(min=EPS))

    # Gather log-prob of target token — clamp target to avoid index OOB
    target_clamped = target.clamp(max=batch.extended_vocab_size - 1)
    gathered = log_probs.gather(2, target_clamped.unsqueeze(-1)).squeeze(-1)
    loss = -(gathered * mask.float()).sum() / mask.float().sum().clamp(min=1)
    return loss


def train_smoke(
    train_records: tuple[ExampleRecord, ...],
    checkpoint_dir: Path,
    config: TrainingConfig | None = None,
    device: torch.device | None = None,
    spider_train_records: tuple[ExampleRecord, ...] | None = None,
    spider_epochs: int = 0,
) -> TrainingResult:
    """Train the LSTM on a bounded smoke slice and save a checkpoint.

    Supports sequenced training: WikiSQL warm-up first, then Spider primary training.
    """
    if config is None:
        config = TrainingConfig()
    if device is None:
        device = torch.device("cpu")

    torch.manual_seed(config.seed)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Slice training examples
    wikisql_examples = train_records[: config.smoke_limit] if config.smoke_limit else train_records
    if not wikisql_examples and not spider_train_records:
        raise ValueError("No training examples provided.")

    # Build unified training vocabulary across both WikiSQL and Spider train splits
    all_train_for_vocab = list(wikisql_examples)
    if spider_train_records:
        all_train_for_vocab.extend(spider_train_records)
    vocabulary = build_training_vocabulary(all_train_for_vocab, max_size=config.max_vocab_size)

    # Save vocabulary alongside checkpoint
    vocab_path = checkpoint_dir / "vocabulary.json"
    vocab_path.write_text(
        json.dumps(
            {
                "tokens": list(vocabulary.tokens),
                "token_to_index": vocabulary.token_to_index,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    model = _make_model(len(vocabulary), config, device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)

    epoch_losses: list[float] = []

    def _train_dataset_epochs(
        dataset_name: str,
        examples: list[ExampleRecord],
        num_epochs: int,
    ) -> None:
        nonlocal epoch_losses
        if not examples or num_epochs <= 0:
            return
        for epoch in range(num_epochs):
            # Shuffle training data each epoch with a deterministic seed
            # so results are reproducible but batch composition varies
            epoch_rng = random.Random(config.seed + epoch)
            shuffled = list(examples)
            epoch_rng.shuffle(shuffled)

            model.train()
            total_loss = 0.0
            total_batches = 0

            total_batches_expected = (len(shuffled) + config.batch_size - 1) // config.batch_size
            for batch_start in range(0, len(shuffled), config.batch_size):
                batch_examples = shuffled[batch_start : batch_start + config.batch_size]
                batch = collate_batch(batch_examples, vocabulary, device)

                optimizer.zero_grad()
                loss = _compute_batch_loss(model, batch, device, config.teacher_forcing_ratio)
                if not math.isfinite(loss.item()):
                    continue
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), config.grad_clip)
                optimizer.step()

                total_loss += loss.item()
                total_batches += 1
                if total_batches % 200 == 0:
                    print(
                        f"    [{dataset_name}] epoch {epoch + 1}/{num_epochs} "
                        f"batch {total_batches}/{total_batches_expected} "
                        f"loss={total_loss / total_batches:.4f}",
                        flush=True,
                    )

            epoch_loss = total_loss / max(total_batches, 1)
            epoch_losses.append(epoch_loss)
            print(f"  [{dataset_name}] epoch {epoch + 1}/{num_epochs}  loss={epoch_loss:.4f}", flush=True)

    # Stage 1: WikiSQL warm-up training
    if wikisql_examples and config.max_epochs > 0:
        print(f"Starting Stage 1: WikiSQL warm-up training ({len(wikisql_examples)} examples)...", flush=True)
        _train_dataset_epochs("WikiSQL", list(wikisql_examples), config.max_epochs)

    # Stage 2: Spider primary training
    if spider_train_records and spider_epochs > 0:
        print(f"Starting Stage 2: Spider primary training ({len(spider_train_records)} examples)...", flush=True)
        _train_dataset_epochs("Spider", list(spider_train_records), spider_epochs)

    # Save checkpoint
    checkpoint_path = checkpoint_dir / "lstm_smoke.pt"
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "config": config.to_dict(),
            "vocab_size": len(vocabulary),
            "vocab_tokens": list(vocabulary.tokens),
        },
        checkpoint_path,
    )

    # Save run metadata
    total_train_count = len(wikisql_examples) + (len(spider_train_records) if spider_train_records else 0)
    meta = {
        "train_examples": total_train_count,
        "vocab_size": len(vocabulary),
        "epoch_losses": epoch_losses,
        "final_loss": epoch_losses[-1] if epoch_losses else float("nan"),
        "config": config.to_dict(),
        "checkpoint": str(checkpoint_path),
    }
    (checkpoint_dir / "training_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    return TrainingResult(
        final_loss=epoch_losses[-1] if epoch_losses else float("nan"),
        epoch_losses=epoch_losses,
        vocab_size=len(vocabulary),
        checkpoint_path=checkpoint_path,
        config=config,
    )


def load_checkpoint(
    checkpoint_path: Path,
    device: torch.device | None = None,
) -> tuple[Seq2SeqLSTM, FixedVocabulary]:
    """Reload a saved checkpoint and reconstruct model + vocabulary.

    Args:
        checkpoint_path: Path to the .pt checkpoint file.
        device: Target device. Defaults to CPU.

    Returns:
        (model, vocabulary) ready for inference.
    """
    if device is None:
        device = torch.device("cpu")

    state = torch.load(checkpoint_path, map_location=device, weights_only=True)
    cfg_dict = state["config"]
    config = TrainingConfig(**{k: v for k, v in cfg_dict.items() if k in TrainingConfig.__dataclass_fields__})

    tokens = tuple(state["vocab_tokens"])
    vocabulary = FixedVocabulary(
        tokens=tokens,
        token_to_index={token: idx for idx, token in enumerate(tokens)},
        counts={},
    )

    model = _make_model(len(vocabulary), config, device)
    model.load_state_dict(state["model_state_dict"])
    model.eval()
    return model, vocabulary
