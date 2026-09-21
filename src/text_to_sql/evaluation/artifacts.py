"""Persistence for reproducible prediction artifacts."""

import json
from collections.abc import Iterable
from pathlib import Path

from ..data.contracts import ExampleRecord
from .metrics import Prediction


def write_prediction_artifacts(
    path: Path,
    examples: Iterable[ExampleRecord],
    predictions: Iterable[Prediction],
) -> int:
    """Write one JSON object per example and return the number written."""
    example_map = {example.example_id: example for example in examples}
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as output:
        for prediction in predictions:
            example = example_map.get(prediction.example_id)
            if example is None:
                raise ValueError(f"prediction has no matching example: {prediction.example_id}")
            record = {
                "example_id": example.example_id,
                "question": example.question,
                "database_id": example.database_id,
                "gold_sql": example.gold_sql,
                "predicted_sql": prediction.predicted_sql,
                "model_name": prediction.model_name,
            }
            output.write(json.dumps(record, sort_keys=True) + "\n")
            count += 1
    return count
