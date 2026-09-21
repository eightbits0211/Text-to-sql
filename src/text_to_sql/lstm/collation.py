"""Dataset collation utilities for the LSTM training loop.

Converts a list of ExampleRecord objects into padded tensors ready for
Seq2SeqLSTM.forward(). Reuses the existing preprocessing contracts.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch

from ..data.contracts import ExampleRecord
from .preprocessing import (
    CopyTarget,
    FixedVocabulary,
    build_copy_target,
    tokenize_example,
)

# Maximum token length guards — prevents OOM on unexpectedly long examples
MAX_SRC_LEN = 256
MAX_TGT_LEN = 128
EOS_TOKEN = "<eos>"
BOS_TOKEN = "<bos>"
PAD_TOKEN = "<pad>"
UNK_TOKEN = "<unk>"


@dataclass
class Batch:
    """One GPU/CPU-ready minibatch."""

    src: torch.Tensor                  # (batch, src_len)
    src_lengths: torch.Tensor          # (batch,)
    src_mask: torch.Tensor             # (batch, src_len) — True where padding
    tgt: torch.Tensor                  # (batch, tgt_len)
    tgt_lengths: torch.Tensor          # (batch,)
    tgt_mask: torch.Tensor             # (batch, tgt_len-1) — True where padding
    src_token_indices: torch.Tensor    # (batch, src_len) extended-vocab index
    extended_vocab_size: int
    extended_vocabs: tuple[tuple[str, ...], ...]  # per-example extended_tokens
    example_ids: tuple[str, ...]


def _encode_encoder_sequence(
    example: ExampleRecord,
    vocabulary: FixedVocabulary,
) -> tuple[list[int], CopyTarget]:
    """Map encoder_tokens to indices and build copy target."""
    tokenized = tokenize_example(example)
    copy_target = build_copy_target(example, vocabulary)

    indices: list[int] = []
    for token in tokenized.encoder_tokens[:MAX_SRC_LEN]:
        idx = vocabulary.get_index(token)
        indices.append(idx if idx is not None else vocabulary.token_to_index.get(UNK_TOKEN, 1))
    return indices, copy_target


def _encode_target_sequence(
    example: ExampleRecord,
    vocabulary: FixedVocabulary,
    copy_target: CopyTarget,
) -> list[int]:
    """Map gold SQL tokens to extended-vocab indices."""
    from .preprocessing import resolve_target_token, tokenize_sql

    bos_idx = vocabulary.token_to_index.get(BOS_TOKEN, 2)
    eos_idx = vocabulary.token_to_index.get(EOS_TOKEN, 3)
    sql_tokens = tokenize_sql(example.gold_sql)
    indices: list[int] = [bos_idx]
    for token in sql_tokens[: MAX_TGT_LEN - 2]:
        res = resolve_target_token(token, vocabulary, copy_target)
        indices.append(res.index)
    indices.append(eos_idx)
    return indices


def collate_batch(
    examples: list[ExampleRecord],
    vocabulary: FixedVocabulary,
    device: torch.device,
) -> Batch:
    """Build a padded minibatch from a list of examples."""
    pad_idx = vocabulary.token_to_index.get(PAD_TOKEN, 0)

    all_src: list[list[int]] = []
    all_tgt: list[list[int]] = []
    all_copy_targets: list[CopyTarget] = []
    example_ids: list[str] = []

    for example in examples:
        src_indices, copy_target = _encode_encoder_sequence(example, vocabulary)
        tgt_indices = _encode_target_sequence(example, vocabulary, copy_target)
        all_src.append(src_indices)
        all_tgt.append(tgt_indices)
        all_copy_targets.append(copy_target)
        example_ids.append(example.example_id)

    # Per-batch extended vocab: union of all extended_tokens lengths
    max_ext = max(len(ct.extended_tokens) for ct in all_copy_targets)

    # Pad sequences
    max_src = max(len(s) for s in all_src)
    max_tgt = max(len(t) for t in all_tgt)

    src_tensor = torch.full((len(examples), max_src), pad_idx, dtype=torch.long, device=device)
    tgt_tensor = torch.full((len(examples), max_tgt), pad_idx, dtype=torch.long, device=device)
    src_ext_tensor = torch.zeros(len(examples), max_src, dtype=torch.long, device=device)
    src_lengths = torch.zeros(len(examples), dtype=torch.long, device=device)
    tgt_lengths = torch.zeros(len(examples), dtype=torch.long, device=device)

    for i, (src_indices, tgt_indices, copy_target) in enumerate(
        zip(all_src, all_tgt, all_copy_targets)
    ):
        src_len = len(src_indices)
        tgt_len = len(tgt_indices)
        src_tensor[i, :src_len] = torch.tensor(src_indices, dtype=torch.long, device=device)
        tgt_tensor[i, :tgt_len] = torch.tensor(tgt_indices, dtype=torch.long, device=device)
        src_lengths[i] = src_len
        tgt_lengths[i] = tgt_len

        # Map each source token position to extended-vocab index
        tokenized = tokenize_example(examples[i])
        from .preprocessing import _normalize_token

        for pos, raw_token in enumerate(tokenized.encoder_tokens[:max_src]):
            normalized = _normalize_token(raw_token)
            ext_idx = copy_target.source_to_index.get(normalized)
            if ext_idx is not None:
                src_ext_tensor[i, pos] = ext_idx

    src_mask = src_tensor == pad_idx
    tgt_mask = tgt_tensor[:, 1:] == pad_idx  # shift: target is tgt[1:]

    return Batch(
        src=src_tensor,
        src_lengths=src_lengths,
        src_mask=src_mask,
        tgt=tgt_tensor,
        tgt_lengths=tgt_lengths,
        tgt_mask=tgt_mask,
        src_token_indices=src_ext_tensor,
        extended_vocab_size=max_ext,
        extended_vocabs=tuple(ct.extended_tokens for ct in all_copy_targets),
        example_ids=tuple(example_ids),
    )
