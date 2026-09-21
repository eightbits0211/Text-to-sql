"""Bounded CPU smoke training loop for the LSTM seq2seq baseline.

Implements teacher-forced NLL training on a capped slice of examples,
checkpointing, and checkpoint reload verification.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

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
) -> TrainingResult:
    """Train the LSTM on a bounded smoke slice and save a checkpoint.

    Args:
        train_records: All training examples (will be sliced by config.smoke_limit).
        checkpoint_dir: Directory to write checkpoint and metadata.
        config: Training hyperparameters. Defaults to TrainingConfig().
        device: Torch device. Defaults to CPU.

    Returns:
        TrainingResult with final loss, losses by epoch, and checkpoint path.
    """
    if config is None:
        config = TrainingConfig()
    if device is None:
        device = torch.device("cpu")

    torch.manual_seed(config.seed)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Slice training examples
    train_examples = train_records[: config.smoke_limit] if config.smoke_limit else train_records
    if not train_examples:
        raise ValueError("No training examples provided.")

    # Build training-only vocabulary
    vocabulary = build_training_vocabulary(train_examples, max_size=config.max_vocab_size)

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
    examples_list = list(train_examples)

    for epoch in range(config.max_epochs):
        model.train()
        total_loss = 0.0
        total_batches = 0

        for batch_start in range(0, len(examples_list), config.batch_size):
            batch_examples = examples_list[batch_start : batch_start + config.batch_size]
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

        epoch_loss = total_loss / max(total_batches, 1)
        epoch_losses.append(epoch_loss)
        print(f"  epoch {epoch + 1}/{config.max_epochs}  loss={epoch_loss:.4f}")

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
    meta = {
        "train_examples": len(train_examples),
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
