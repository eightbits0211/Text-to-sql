"""LSTMBaseline adapter — exposes the same interface as TemplateBaseline.

Uses greedy decoding with the pointer-generator to produce one SQL string
per example. Falls back to an empty string on any decoding error.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import torch

from ..data.contracts import DatasetSplit, ExampleRecord
from ..evaluation.metrics import EvaluationReport, Prediction, evaluate_predictions
from .collation import BOS_TOKEN, EOS_TOKEN, MAX_TGT_LEN, PAD_TOKEN, UNK_TOKEN
from .model import Seq2SeqLSTM
from .preprocessing import (
    CopyTarget,
    FixedVocabulary,
    _normalize_token,
    build_copy_target,
    tokenize_example,
)
from .sql_repair import repair_sql
from .training import TrainingConfig, TrainingResult, load_checkpoint, train_smoke


class LSTMBaseline:
    """Trainable LSTM seq2seq baseline with pointer-generator copying.

    Public interface mirrors TemplateBaseline so the same evaluation harness
    and CLI can use either without modification.
    """

    name = "lstm-baseline"

    def __init__(
        self,
        config: TrainingConfig | None = None,
        device: torch.device | None = None,
    ) -> None:
        self._config = config or TrainingConfig()
        self._device = device or torch.device("cpu")
        self._model: Seq2SeqLSTM | None = None
        self._vocabulary: FixedVocabulary | None = None

    # ------------------------------------------------------------------
    # Shared adapter interface
    # ------------------------------------------------------------------

    def fit(
        self,
        examples: Iterable[ExampleRecord],
        checkpoint_dir: Path | None = None,
        spider_examples: Iterable[ExampleRecord] | None = None,
        spider_epochs: int = 0,
    ) -> LSTMBaseline:
        """Train on the provided examples and cache the model in-process.

        Supports two-stage training: WikiSQL warm-up first, then Spider primary training.
        """
        records = tuple(examples)
        spider_records = tuple(spider_examples) if spider_examples is not None else None
        if checkpoint_dir is None:
            checkpoint_dir = Path("artifacts/lstm-smoke")

        result: TrainingResult = train_smoke(
            records,
            checkpoint_dir,
            config=self._config,
            device=self._device,
            spider_train_records=spider_records,
            spider_epochs=spider_epochs,
        )
        self._model, self._vocabulary = load_checkpoint(result.checkpoint_path, self._device)
        return self

    def load(self, checkpoint_path: Path) -> LSTMBaseline:
        """Load from an existing checkpoint file."""
        self._model, self._vocabulary = load_checkpoint(checkpoint_path, self._device)
        return self

    def predict(self, question: str, schema_text: str, database_id: str = "unknown") -> str:
        """Generate one SQL string for a question/schema pair.

        Returns an empty string if the model is untrained or decoding fails.
        """
        if self._model is None or self._vocabulary is None:
            return ""
        try:
            raw_sql = self._greedy_decode(question, schema_text, database_id)
            return repair_sql(raw_sql, schema_text, database_id)
        except Exception:  # noqa: BLE001 — surface all errors as empty predictions
            return ""

    def predict_record(self, example: ExampleRecord) -> Prediction:
        return Prediction(
            example_id=example.example_id,
            model_name=self.name,
            predicted_sql=self.predict(
                example.question, example.schema_text, example.database_id
            ),
        )

    def predict_records(self, examples: Iterable[ExampleRecord]) -> tuple[Prediction, ...]:
        return tuple(self.predict_record(example) for example in examples)

    def evaluate(
        self,
        examples: Iterable[ExampleRecord],
        database_root: object | None = None,
    ) -> EvaluationReport:
        del database_root
        records = tuple(examples)
        return evaluate_predictions(records, self.predict_records(records))

    # ------------------------------------------------------------------
    # Greedy decoder
    # ------------------------------------------------------------------

    def _greedy_decode(self, question: str, schema_text: str, database_id: str) -> str:
        """Run greedy decoding for a single example (no batching)."""
        assert self._model is not None
        assert self._vocabulary is not None

        vocabulary = self._vocabulary
        model = self._model
        device = self._device

        # Build a temporary ExampleRecord shell just for preprocessing
        from pathlib import Path as _Path

        from ..data.contracts import QueryDifficulty, QueryStructure

        fake_example = ExampleRecord(
            example_id="decode",
            dataset="decode",
            split=DatasetSplit.DEV,
            database_id=database_id,
            database_path=_Path("/dev/null"),
            question=question,
            schema_text=schema_text,
            gold_sql="SELECT 1",
            difficulty=QueryDifficulty.UNKNOWN,
            query_structure=QueryStructure.SINGLE_TABLE,
        )

        tokenized = tokenize_example(fake_example)
        copy_target = build_copy_target(fake_example, vocabulary)
        extended_vocab_size = len(copy_target.extended_tokens)

        # Build encoder input tensor
        pad_idx = vocabulary.token_to_index.get(PAD_TOKEN, 0)
        unk_idx = vocabulary.token_to_index.get(UNK_TOKEN, 1)
        src_indices = [
            (vocabulary.get_index(tok) if vocabulary.get_index(tok) is not None else unk_idx)
            for tok in tokenized.encoder_tokens
        ]
        src = torch.tensor([src_indices], dtype=torch.long, device=device)
        src_lengths = torch.tensor([len(src_indices)], dtype=torch.long, device=device)
        src_mask = src == pad_idx

        # Build src_token_indices for copy distribution
        src_ext = torch.zeros(1, len(src_indices), dtype=torch.long, device=device)
        for pos, raw_token in enumerate(tokenized.encoder_tokens):
            normalized = _normalize_token(raw_token)
            ext_idx = copy_target.source_to_index.get(normalized)
            if ext_idx is not None:
                src_ext[0, pos] = ext_idx

        model.eval()
        with torch.no_grad():
            encoder_outputs, decoder_state = model.encoder(src, src_lengths)

            bos_idx = vocabulary.token_to_index.get(BOS_TOKEN, 2)
            eos_idx = vocabulary.token_to_index.get(EOS_TOKEN, 3)

            prev_token = torch.tensor([bos_idx], dtype=torch.long, device=device)
            prev_context = torch.zeros(1, model.hidden_dim, device=device)

            decoded_indices: list[int] = []
            for _ in range(MAX_TGT_LEN):
                combined, attn_weights, decoder_state, embedded = model.decoder.forward_step(
                    prev_token, prev_context, decoder_state, encoder_outputs, src_mask
                )
                prev_context = combined[:, : model.hidden_dim]

                full_dist = model.decoder.compute_output_distribution(
                    combined, embedded, attn_weights, extended_vocab_size, src_ext
                )
                full_dist[:, unk_idx] = -float("inf")
                full_dist[:, pad_idx] = -float("inf")
                token_idx = full_dist.argmax(-1).item()
                if token_idx == eos_idx:
                    break
                decoded_indices.append(token_idx)
                prev_token = torch.tensor(
                    [min(token_idx, model.vocab_size - 1)], dtype=torch.long, device=device
                )

        return self._render_tokens(decoded_indices, copy_target)

    def _render_tokens(self, indices: list[int], copy_target: CopyTarget) -> str:
        """Convert decoded indices back to a SQL string."""
        extended_tokens = copy_target.extended_tokens
        tokens: list[str] = []
        for idx in indices:
            if idx < len(extended_tokens):
                tok = extended_tokens[idx]
                if tok not in ("<pad>", "<unk>", "<bos>", "<eos>", "<schema_sep>"):
                    tokens.append(tok)
        return " ".join(tokens)
