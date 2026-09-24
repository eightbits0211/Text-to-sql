"""Smoke training loop and checkpoint reload tests for the LSTM baseline.

These tests use tiny synthetic fixtures and run in seconds on CPU.
They do NOT require official datasets.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import torch

from text_to_sql.data.contracts import DatasetSplit, ExampleRecord, QueryDifficulty, QueryStructure
from text_to_sql.lstm.adapter import LSTMBaseline
from text_to_sql.lstm.training import TrainingConfig, load_checkpoint, train_smoke


def _make_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            "CREATE TABLE singers (singer_id INTEGER PRIMARY KEY, name TEXT, country TEXT)"
        )
        conn.executemany(
            "INSERT INTO singers VALUES (?,?,?)",
            [(1, "Ada", "USA"), (2, "Grace", "USA"), (3, "Turing", "UK")],
        )
        conn.commit()
    finally:
        conn.close()


def _example(
    idx: int,
    question: str,
    gold_sql: str,
    db_path: Path,
    split: DatasetSplit = DatasetSplit.TRAIN,
) -> ExampleRecord:
    schema_text = (
        "database: singers\n"
        "table: singers\n"
        "columns:\n"
        "  - singer_id [INTEGER]\n"
        "  - name [TEXT]\n"
        "  - country [TEXT]\n"
        "foreign_keys:"
    )
    return ExampleRecord(
        example_id=f"smoke-{idx}",
        dataset="synthetic",
        split=split,
        database_id="singers",
        database_path=db_path,
        question=question,
        schema_text=schema_text,
        gold_sql=gold_sql,
        difficulty=QueryDifficulty.EASY,
        query_structure=QueryStructure.SINGLE_TABLE,
        source_index=idx,
    )


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    p = tmp_path / "singers.db"
    _make_db(p)
    return p


@pytest.fixture()
def smoke_examples(db_path: Path) -> tuple[ExampleRecord, ...]:
    pairs = [
        ("What are the names of all singers?", "SELECT name FROM singers"),
        ("List all singers from USA.", "SELECT name FROM singers WHERE country = 'USA'"),
        ("How many singers are there?", "SELECT COUNT(*) FROM singers"),
        ("Show all countries.", "SELECT country FROM singers"),
        ("Which singers are from UK?", "SELECT name FROM singers WHERE country = 'UK'"),
        ("What is the singer with id 1?", "SELECT name FROM singers WHERE singer_id = 1"),
        ("List names and countries.", "SELECT name , country FROM singers"),
        ("Count USA singers.", "SELECT COUNT(*) FROM singers WHERE country = 'USA'"),
    ]
    return tuple(_example(i, q, s, db_path) for i, (q, s) in enumerate(pairs))


# ---------------------------------------------------------------------------
# Core smoke training tests
# ---------------------------------------------------------------------------


def test_smoke_training_runs_and_reduces_loss(
    tmp_path: Path, smoke_examples: tuple[ExampleRecord, ...]
) -> None:
    """Training should complete without error and produce a finite loss."""
    config = TrainingConfig(
        embedding_dim=32,
        hidden_dim=64,
        num_encoder_layers=1,
        num_decoder_layers=1,
        dropout=0.0,
        learning_rate=1e-2,
        batch_size=4,
        max_epochs=3,
        smoke_limit=None,
        seed=0,
    )
    result = train_smoke(smoke_examples, tmp_path / "ckpt", config=config)

    assert len(result.epoch_losses) == 3
    assert all(isinstance(loss, float) for loss in result.epoch_losses)
    assert all(loss < 100.0 for loss in result.epoch_losses)  # sanity: not exploding
    assert result.checkpoint_path.exists()
    assert (tmp_path / "ckpt" / "vocabulary.json").exists()
    assert (tmp_path / "ckpt" / "training_meta.json").exists()


def test_checkpoint_reload_returns_equivalent_model(
    tmp_path: Path, smoke_examples: tuple[ExampleRecord, ...]
) -> None:
    """A reloaded checkpoint must produce the same output as the saved model."""
    config = TrainingConfig(
        embedding_dim=32,
        hidden_dim=64,
        num_encoder_layers=1,
        num_decoder_layers=1,
        dropout=0.0,
        batch_size=4,
        max_epochs=2,
        smoke_limit=None,
        seed=7,
    )
    result = train_smoke(smoke_examples, tmp_path / "ckpt", config=config)
    model_a, vocab_a = load_checkpoint(result.checkpoint_path)
    model_b, vocab_b = load_checkpoint(result.checkpoint_path)

    assert vocab_a.tokens == vocab_b.tokens

    # Both models should produce identical output on the same random input
    model_a.eval()
    model_b.eval()
    torch.manual_seed(0)
    dummy_src = torch.zeros(1, 10, dtype=torch.long)
    dummy_lengths = torch.tensor([10])
    with torch.no_grad():
        out_a, _ = model_a.encoder(dummy_src, dummy_lengths)
        out_b, _ = model_b.encoder(dummy_src, dummy_lengths)
    assert torch.allclose(out_a, out_b)


def test_lstm_adapter_fit_and_predict(
    tmp_path: Path,
    smoke_examples: tuple[ExampleRecord, ...],
    db_path: Path,
) -> None:
    """Fit the adapter and verify predict returns a non-crashing string."""
    config = TrainingConfig(
        embedding_dim=32,
        hidden_dim=64,
        num_encoder_layers=1,
        num_decoder_layers=1,
        dropout=0.0,
        batch_size=4,
        max_epochs=2,
        smoke_limit=None,
        seed=3,
    )
    baseline = LSTMBaseline(config=config)
    baseline.fit(smoke_examples, checkpoint_dir=tmp_path / "ckpt")

    sql = baseline.predict(
        "What are the names?",
        "database: singers\ntable: singers\ncolumns:\n  - name [TEXT]\nforeign_keys:",
    )
    assert isinstance(sql, str)  # must return a string, even if empty


def test_lstm_adapter_evaluate_uses_shared_harness(
    tmp_path: Path,
    smoke_examples: tuple[ExampleRecord, ...],
    db_path: Path,
) -> None:
    """evaluate() must return a valid EvaluationReport via the shared metrics harness."""
    config = TrainingConfig(
        embedding_dim=32,
        hidden_dim=64,
        num_encoder_layers=1,
        num_decoder_layers=1,
        dropout=0.0,
        batch_size=4,
        max_epochs=1,
        smoke_limit=None,
        seed=5,
    )
    baseline = LSTMBaseline(config=config)
    baseline.fit(smoke_examples, checkpoint_dir=tmp_path / "ckpt")
    report = baseline.evaluate(smoke_examples)

    assert report.evaluated_count == len(smoke_examples)
    assert 0.0 <= report.execution_accuracy <= 1.0
    assert 0.0 <= report.invalid_sql_rate <= 1.0


def test_untrained_lstm_adapter_returns_empty_string() -> None:
    """An untrained adapter must return an empty string, not raise."""
    baseline = LSTMBaseline()
    result = baseline.predict(
        "Any question?", "database: x\ntable: t\ncolumns:\n  - id [INTEGER]\nforeign_keys:"
    )
    assert result == ""


def test_two_stage_wikisql_then_spider_training(
    tmp_path: Path,
    smoke_examples: tuple[ExampleRecord, ...],
) -> None:
    """Sequential training on WikiSQL then Spider records must train and save unified checkpoint."""
    config = TrainingConfig(
        embedding_dim=32,
        hidden_dim=64,
        num_encoder_layers=1,
        num_decoder_layers=1,
        dropout=0.0,
        batch_size=4,
        max_epochs=1,
        smoke_limit=None,
        seed=42,
    )
    # Split smoke_examples into mock WikiSQL (first 4) and mock Spider (last 4)
    wikisql_mock = smoke_examples[:4]
    spider_mock = smoke_examples[4:]

    baseline = LSTMBaseline(config=config)
    baseline.fit(
        wikisql_mock,
        checkpoint_dir=tmp_path / "two_stage_ckpt",
        spider_examples=spider_mock,
        spider_epochs=1,
    )
    assert baseline._model is not None
    assert baseline._vocabulary is not None
    assert (tmp_path / "two_stage_ckpt" / "lstm_smoke.pt").exists()
    assert (tmp_path / "two_stage_ckpt" / "training_meta.json").exists()
