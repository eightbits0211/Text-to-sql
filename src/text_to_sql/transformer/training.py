"""Plain PyTorch fine-tuning loop for T5 (no Trainer, so the live demo can print every step)."""

from __future__ import annotations

import logging
import math
import random
import time
from collections.abc import Sequence

import torch

from ..config import seed_everything
from ..data.contracts import ExampleRecord
from .serialization import build_t5_input

LOGGER = logging.getLogger(__name__)


def _batches(pairs: list[tuple[str, str]], batch_size: int, shuffle: bool, rng: random.Random):
    order = list(range(len(pairs)))
    if shuffle:
        rng.shuffle(order)
    for start in range(0, len(order), batch_size):
        yield [pairs[i] for i in order[start : start + batch_size]]


def _pairs(examples: Sequence[ExampleRecord]) -> list[tuple[str, str]]:
    return [(build_t5_input(ex.question, ex.schema_text), ex.gold_sql) for ex in examples]


def _loss(model, tokenizer, batch, config, device) -> torch.Tensor:
    sources, targets = zip(*batch)
    encoded = tokenizer(
        list(sources),
        max_length=config.max_input_length,
        truncation=True,
        padding=True,
        return_tensors="pt",
    ).to(device)
    labels = tokenizer(
        list(targets),
        max_length=config.max_output_length,
        truncation=True,
        padding=True,
        return_tensors="pt",
    ).input_ids.to(device)
    labels[labels == tokenizer.pad_token_id] = -100
    return model(**encoded, labels=labels).loss


# Characters SQL needs that the T5 SentencePiece vocabulary maps to <unk>.
SQL_EXTRA_TOKENS = ("<", "<=")


def add_sql_tokens(tokenizer, model) -> int:
    """Add SQL characters missing from the T5 vocabulary and resize the embeddings."""
    missing = [
        token
        for token in SQL_EXTRA_TOKENS
        if tokenizer.unk_token_id in tokenizer(token, add_special_tokens=False).input_ids
    ]
    added = tokenizer.add_tokens(missing) if missing else 0
    if added:
        model.resize_token_embeddings(len(tokenizer))
    return added


def train_t5(config, examples, dev_examples, device, log_every: int = 50, on_epoch_end=None):
    """Fine-tune ``config.checkpoint``; ``on_epoch_end(model, tokenizer, record)`` runs after each epoch."""
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, get_linear_schedule_with_warmup

    if not examples:
        raise ValueError("No training examples")
    seed_everything(config.seed)
    rng = random.Random(config.seed)
    tokenizer = AutoTokenizer.from_pretrained(config.checkpoint)
    model = AutoModelForSeq2SeqLM.from_pretrained(config.checkpoint)
    LOGGER.info("added %d SQL tokens to the T5 vocabulary", add_sql_tokens(tokenizer, model))
    model = model.to(device)
    train_pairs, dev_pairs = _pairs(examples), _pairs(dev_examples)

    steps_per_epoch = math.ceil(
        len(train_pairs) / config.batch_size / config.gradient_accumulation_steps
    )
    total_steps = steps_per_epoch * config.epochs
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
    )
    scheduler = get_linear_schedule_with_warmup(
        optimizer, int(config.warmup_ratio * total_steps), total_steps
    )

    history: list[dict[str, float]] = []
    step = 0
    started = time.monotonic()
    for epoch in range(1, config.epochs + 1):
        model.train()
        running, count = 0.0, 0
        for index, batch in enumerate(_batches(train_pairs, config.batch_size, True, rng), start=1):
            loss = _loss(model, tokenizer, batch, config, device)
            (loss / config.gradient_accumulation_steps).backward()
            running += loss.item()
            count += 1
            if index % config.gradient_accumulation_steps == 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
                step += 1
                if log_every and step % log_every == 0:
                    LOGGER.info("step %d  loss %.4f", step, running / count)
        record = {"epoch": float(epoch), "train_loss": running / max(count, 1)}
        if dev_pairs:
            model.eval()
            with torch.no_grad():
                losses = [
                    _loss(model, tokenizer, batch, config, device).item()
                    for batch in _batches(dev_pairs, config.batch_size, False, rng)
                ]
            record["dev_loss"] = sum(losses) / len(losses)
        record["elapsed_s"] = time.monotonic() - started
        history.append(record)
        LOGGER.info("epoch %d %s", epoch, {k: round(v, 4) for k, v in record.items()})
        if on_epoch_end is not None:
            on_epoch_end(model, tokenizer, record)
    return model, tokenizer, history
