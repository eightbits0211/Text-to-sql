"""T5Baseline adapter — same interface as TemplateBaseline and LSTMBaseline."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

import torch

from ..config import seed_everything
from ..data.contracts import ExampleRecord
from ..data.schema import DatabaseSchema, serialize_schema
from ..evaluation.metrics import EvaluationReport, Prediction, evaluate_predictions
from .serialization import build_t5_input

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class T5Config:
    checkpoint: str = "google-t5/t5-base"
    max_input_length: int = 512
    max_output_length: int = 256
    learning_rate: float = 1e-4
    batch_size: int = 8
    gradient_accumulation_steps: int = 1
    epochs: int = 30
    warmup_ratio: float = 0.05
    weight_decay: float = 0.0
    seed: int = 42
    num_beams: int = 4


def select_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class T5Baseline:
    name = "t5"

    def __init__(self, config: T5Config | None = None, device: torch.device | None = None) -> None:
        self.config = config or T5Config()
        self.device = device or select_device()
        self._model = None
        self._tokenizer = None

    # ------------------------------------------------------------------
    # Loading and training
    # ------------------------------------------------------------------

    @classmethod
    def from_checkpoint(cls, path: Path, device: torch.device | None = None) -> T5Baseline:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        config_path = path / "t5_config.json"
        config = (
            T5Config(**json.loads(config_path.read_text())) if config_path.is_file() else T5Config()
        )
        baseline = cls(config, device)
        baseline._tokenizer = AutoTokenizer.from_pretrained(path)
        baseline._model = AutoModelForSeq2SeqLM.from_pretrained(path).to(baseline.device).eval()
        return baseline

    def save(self, path: Path) -> None:
        if self._model is None or self._tokenizer is None:
            raise RuntimeError("Cannot save an untrained T5Baseline")
        path.mkdir(parents=True, exist_ok=True)
        self._model.save_pretrained(path)
        self._tokenizer.save_pretrained(path)
        (path / "t5_config.json").write_text(json.dumps(asdict(self.config), indent=2))

    def fit(
        self,
        examples: Sequence[ExampleRecord],
        output_dir: Path | None = None,
        dev_examples: Sequence[ExampleRecord] = (),
        log_every: int = 50,
        on_epoch_end=None,
    ) -> list[dict[str, float]]:
        from .training import train_t5

        model, tokenizer, history = train_t5(
            self.config,
            examples,
            dev_examples,
            self.device,
            log_every=log_every,
            on_epoch_end=on_epoch_end,
        )
        self._model, self._tokenizer = model.eval(), tokenizer
        if output_dir is not None:
            self.save(output_dir)
        return history

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def encode_input(self, question: str, schema: str | DatabaseSchema) -> str:
        schema_text = schema if isinstance(schema, str) else serialize_schema(schema)
        return build_t5_input(question, schema_text)

    @torch.no_grad()
    def generate_candidates(
        self,
        question: str,
        schema: str | DatabaseSchema,
        num_beams: int | None = None,
        num_return_sequences: int = 1,
        logits_processor=None,
    ) -> list[str]:
        """Beam-search candidates, best first."""
        if self._model is None or self._tokenizer is None:
            raise RuntimeError("T5Baseline has no model; train it or load a checkpoint")
        beams = num_beams or self.config.num_beams
        encoded = self._tokenizer(
            self.encode_input(question, schema),
            max_length=self.config.max_input_length,
            truncation=True,
            return_tensors="pt",
        ).to(self.device)
        outputs = self._model.generate(
            **encoded,
            max_length=self.config.max_output_length,
            num_beams=max(beams, num_return_sequences),
            num_return_sequences=num_return_sequences,
            logits_processor=logits_processor,
        )
        return [
            text.strip() for text in self._tokenizer.batch_decode(outputs, skip_special_tokens=True)
        ]

    def predict(
        self, question: str, schema: str | DatabaseSchema, database_id: str = "unknown"
    ) -> str:
        del database_id
        return self.generate_candidates(question, schema)[0]

    def predict_record(self, example: ExampleRecord) -> Prediction:
        return Prediction(
            example_id=example.example_id,
            model_name=self.name,
            predicted_sql=self.predict(example.question, example.schema_text, example.database_id),
        )

    @torch.no_grad()
    def generate_batch(
        self, examples: Sequence[ExampleRecord], num_beams: int | None = None
    ) -> list[str]:
        """Top beam for each example, decoded in one padded batch."""
        if self._model is None or self._tokenizer is None:
            raise RuntimeError("T5Baseline has no model; train it or load a checkpoint")
        encoded = self._tokenizer(
            [self.encode_input(ex.question, ex.schema_text) for ex in examples],
            max_length=self.config.max_input_length,
            truncation=True,
            padding=True,
            return_tensors="pt",
        ).to(self.device)
        outputs = self._model.generate(
            **encoded,
            max_length=self.config.max_output_length,
            num_beams=num_beams or self.config.num_beams,
        )
        return [
            text.strip() for text in self._tokenizer.batch_decode(outputs, skip_special_tokens=True)
        ]

    def predict_records(
        self,
        examples: Iterable[ExampleRecord],
        batch_size: int = 32,
        num_beams: int | None = None,
    ) -> tuple[Prediction, ...]:
        records = tuple(examples)
        predictions: list[Prediction] = []
        for start in range(0, len(records), batch_size):
            chunk = records[start : start + batch_size]
            for example, sql in zip(chunk, self.generate_batch(chunk, num_beams), strict=True):
                predictions.append(Prediction(example.example_id, self.name, sql))
        return tuple(predictions)

    def evaluate(
        self, examples: Iterable[ExampleRecord], database_root: object | None = None
    ) -> EvaluationReport:
        del database_root
        records = tuple(examples)
        return evaluate_predictions(records, self.predict_records(records))


__all__ = ["T5Baseline", "T5Config", "seed_everything", "select_device"]
