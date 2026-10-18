"""GPTBaseline: open-weight GPT model (default gpt-oss-20b) via Hugging Face transformers."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import torch

from ..data.contracts import ExampleRecord
from ..evaluation.metrics import EvaluationReport, Prediction, evaluate_predictions
from .prompts import FewShotSelector, build_messages, extract_sql

LOGGER = logging.getLogger(__name__)

# gpt-oss emits its reasoning in an "analysis" channel before the "final" answer.
_FINAL_MARKER = "<|channel|>final<|message|>"


@dataclass(frozen=True)
class GPTConfig:
    model_id: str = "openai/gpt-oss-20b"
    shots: int = 0
    sample_rows: int = 3
    max_new_tokens: int = 1024
    reasoning_effort: str = "low"
    batch_size: int = 8
    # The HPC nodes lack Python.h, so Triton cannot build the MXFP4 kernels;
    # dequantize to bf16 (~42 GB) instead.
    dequantize: bool = False


class GPTBaseline:
    def __init__(
        self,
        config: GPTConfig | None = None,
        few_shot_pool: Sequence[ExampleRecord] = (),
        model=None,
        tokenizer=None,
    ) -> None:
        self.config = config or GPTConfig()
        self.name = f"gpt-{self.config.shots}shot"
        self._selector = FewShotSelector(few_shot_pool) if few_shot_pool else None
        self._model, self._tokenizer = model, tokenizer

    def load(self) -> GPTBaseline:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(self.config.model_id, padding_side="left")
        kwargs = {}
        if self.config.dequantize:
            from transformers import Mxfp4Config

            kwargs = {"quantization_config": Mxfp4Config(dequantize=True), "dtype": torch.bfloat16}
        else:
            kwargs = {"dtype": "auto"}
        self._model = AutoModelForCausalLM.from_pretrained(
            self.config.model_id, device_map="auto", **kwargs
        ).eval()
        return self

    def messages_for(self, example: ExampleRecord) -> list[dict[str, str]]:
        shots = self._selector.select(example, self.config.shots) if self._selector else []
        return build_messages(example, shots, self.config.sample_rows)

    @torch.no_grad()
    def generate(self, conversations: Sequence[list[dict[str, str]]]) -> list[str]:
        if self._model is None or self._tokenizer is None:
            raise RuntimeError("GPTBaseline has no model; call load() first")
        prompts = [
            self._tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=False,
                reasoning_effort=self.config.reasoning_effort,
            )
            for messages in conversations
        ]
        encoded = self._tokenizer(
            prompts, return_tensors="pt", padding=True, add_special_tokens=False
        ).to(self._model.device)
        outputs = self._model.generate(
            **encoded,
            max_new_tokens=self.config.max_new_tokens,
            do_sample=False,
            pad_token_id=self._tokenizer.pad_token_id or self._tokenizer.eos_token_id,
        )
        new_tokens = outputs[:, encoded.input_ids.shape[1] :]
        texts = self._tokenizer.batch_decode(new_tokens, skip_special_tokens=False)
        return [final_answer(text) for text in texts]

    def predict_records(self, examples: Iterable[ExampleRecord]) -> tuple[Prediction, ...]:
        records = tuple(examples)
        predictions: list[Prediction] = []
        size = self.config.batch_size
        for start in range(0, len(records), size):
            chunk = records[start : start + size]
            responses = self.generate([self.messages_for(ex) for ex in chunk])
            for example, response in zip(chunk, responses, strict=True):
                predictions.append(Prediction(example.example_id, self.name, extract_sql(response)))
            LOGGER.info("decoded %d/%d", len(predictions), len(records))
        return tuple(predictions)

    def predict_record(self, example: ExampleRecord) -> Prediction:
        return self.predict_records((example,))[0]

    def evaluate(
        self, examples: Iterable[ExampleRecord], database_root: object | None = None
    ) -> EvaluationReport:
        del database_root
        records = tuple(examples)
        return evaluate_predictions(records, self.predict_records(records))


def final_answer(text: str) -> str:
    """Keep only gpt-oss's final channel; other models' text passes through."""
    if _FINAL_MARKER in text:
        text = text.split(_FINAL_MARKER, 1)[1]
    for stop in ("<|return|>", "<|end|>", "<|endoftext|>"):
        text = text.split(stop, 1)[0]
    return text.strip()
