"""Inference-time ablation of the LSTM baseline on one fixed checkpoint.

Every row decodes the *same* trained weights; rows differ only in decoding
constraints (schema-markup mask, copy feedback) and post-processing
(surface-form rendering, SQL repair). This isolates what each inference
component contributes without retraining.

Rows:
    raw              greedy tokens joined with spaces, no repair
    as_submitted     + repair v1 (the configuration scored in Job 361547)
    render           + surface-form rendering (identifier spelling, quoted literals)
    mask             as_submitted + schema-markup token mask
    mask_render      mask + rendering (the final configuration, DecodeOptions())
    mask_render_unk  mask_render + copy tokens fed back as <unk>

Usage:
    uv run python scripts/run_ablation.py --checkpoint .../spider_checkpoint.pt \
        --dataset spider --split dev --output-dir .../ablation/spider-dev --with-template
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import time
from dataclasses import asdict
from pathlib import Path

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")

import torch

from scripts.run_official_spider_eval import parse_scores, write_eval_files
from text_to_sql.baselines import TemplateBaseline
from text_to_sql.data.contracts import DatasetSplit, ExampleRecord
from text_to_sql.data.spider import load_spider
from text_to_sql.data.wikisql import load_wikisql
from text_to_sql.evaluation.artifacts import write_prediction_artifacts
from text_to_sql.evaluation.metrics import EvaluationReport, Prediction, evaluate_predictions
from text_to_sql.evaluation.reports import write_evaluation_reports
from text_to_sql.evaluation.statistics import bootstrap_interval, mcnemar_exact
from text_to_sql.lstm import DecodeOptions, LSTMBaseline

_DATA = Path(os.environ.get("TEXT2SQL_DATA_ROOT", "/Users/roshini/datasets/text-to-sql"))
_SPIDER = _DATA / "spider" / "spider_data"
_WIKISQL = _DATA / "wikisql" / "data"

PASSES = {
    "nomask": DecodeOptions(mask_schema_markup=False, copy_feedback_unk=False),
    "mask": DecodeOptions(mask_schema_markup=True, copy_feedback_unk=False),
    "mask_unk": DecodeOptions(mask_schema_markup=True, copy_feedback_unk=True),
}
# variant -> (decode pass, repair, restore_surface_forms)
VARIANTS = {
    "raw": ("nomask", False, False),
    "as_submitted": ("nomask", True, False),
    "render": ("nomask", True, True),
    "mask": ("mask", True, False),
    "mask_render": ("mask", True, True),
    "mask_render_unk": ("mask_unk", True, True),
}


def load_records(dataset: str, split: str, limit: int | None) -> tuple[ExampleRecord, ...]:
    if dataset == "spider":
        source = _SPIDER / ("dev.json" if split == "dev" else "test.json")
        tables = _SPIDER / ("tables.json" if split == "dev" else "test_tables.json")
        databases = _SPIDER / ("database" if split == "dev" else "test_database")
        result = load_spider(
            source,
            tables,
            databases,
            split=DatasetSplit.DEV if split == "dev" else DatasetSplit.TEST,
            smoke_limit=limit,
        )
    else:
        result = load_wikisql(
            _WIKISQL / f"{split}.jsonl",
            _WIKISQL,
            split=DatasetSplit.DEV if split == "dev" else DatasetSplit.TEST,
            database_pattern=f"{split}.db",
            table_metadata_path=_WIKISQL / f"{split}.tables.jsonl",
            smoke_limit=limit,
        )
    print(f"{dataset}/{split}: retained={len(result.records)} excluded={len(result.exclusions)}")
    return result.records


_WORKER: LSTMBaseline | None = None


def _device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _init_worker(checkpoint: str) -> None:
    global _WORKER
    if _device().type == "cpu":
        torch.set_num_threads(1)
    _WORKER = LSTMBaseline.from_checkpoint(Path(checkpoint), device=_device())


def _decode_chunk(args: tuple[str, list[tuple[str, str, str, str]]]) -> list[tuple[str, list[str]]]:
    pass_name, items = args
    assert _WORKER is not None
    _WORKER.decode_options = PASSES[pass_name]
    decoded = []
    for example_id, question, schema_text, database_id in items:
        try:
            tokens = _WORKER.decode_tokens(question, schema_text, database_id)
        except (AssertionError, IndexError, KeyError, RuntimeError, ValueError):
            tokens = []
        decoded.append((example_id, tokens))
    return decoded


def decode_all(
    checkpoint: Path, records: tuple[ExampleRecord, ...], pass_names: list[str], workers: int
) -> dict[str, dict[str, list[str]]]:
    items = [(r.example_id, r.question, r.schema_text, r.database_id) for r in records]
    chunk = max(1, len(items) // (workers * 4))
    chunks = [items[i : i + chunk] for i in range(0, len(items), chunk)]
    results: dict[str, dict[str, list[str]]] = {}
    with mp.get_context("spawn").Pool(workers, _init_worker, (str(checkpoint),)) as pool:
        for pass_name in pass_names:
            start = time.time()
            decoded: dict[str, list[str]] = {}
            for part in pool.imap(_decode_chunk, [(pass_name, c) for c in chunks]):
                decoded.update(part)
            results[pass_name] = decoded
            print(f"  decoded pass={pass_name} in {time.time() - start:.0f}s", flush=True)
    return results


def _summary(report: EvaluationReport) -> dict[str, object]:
    def interval(values: list[bool]) -> dict[str, float]:
        ci = bootstrap_interval(values)
        return {"estimate": ci.estimate, "ci95_low": ci.lower, "ci95_high": ci.upper}

    items = report.examples
    return {
        "n": report.evaluated_count,
        "execution_strict": interval([i.execution_match for i in items]),
        "execution_official_semantics": interval([i.execution_match_official for i in items]),
        "string_match": interval([i.exact_match for i in items]),
        "invalid_sql": interval([i.invalid_sql for i in items]),
    }


def _official(output_dir: Path, split: str) -> dict[str, dict[str, float]] | None:
    import subprocess

    tools = _DATA / "tools"
    gold, pred = write_eval_files(
        output_dir / "predictions.jsonl",
        output_dir / "official",
        database_dir=_SPIDER / ("database" if split == "dev" else "test_database"),
    )
    completed = subprocess.run(
        [
            str(tools / "evalenv" / "bin" / "python"),
            "evaluation.py",
            "--gold",
            str(gold.resolve()),
            "--pred",
            str(pred.resolve()),
            "--db",
            str(_SPIDER / ("database" if split == "dev" else "test_database")),
            "--table",
            str(_SPIDER / ("tables.json" if split == "dev" else "test_tables.json")),
            "--etype",
            "all",
        ],
        cwd=tools / "test-suite-sql-eval",
        capture_output=True,
        text=True,
        check=False,
    )
    (output_dir / "official" / "official_eval.txt").write_text(completed.stdout + completed.stderr)
    return parse_scores(completed.stdout) if completed.returncode == 0 else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--dataset", choices=("spider", "wikisql"), default="spider")
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--variants", default=",".join(VARIANTS))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--sample", type=int, default=None, help="Seeded random sample size (after loading)"
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--with-template", action="store_true")
    parser.add_argument("--no-official", action="store_true")
    args = parser.parse_args()

    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    records = load_records(args.dataset, args.split, args.limit)
    if args.sample and args.sample < len(records):
        import random

        chosen = sorted(random.Random(42).sample(range(len(records)), args.sample))
        records = tuple(records[i] for i in chosen)
        print(f"  seeded random sample: {len(records)} examples (seed 42)")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    cache_path = args.output_dir / "decoded_tokens.json"
    cache: dict[str, dict[str, list[str]]] = (
        json.loads(cache_path.read_text()) if cache_path.is_file() else {}
    )
    needed = sorted({VARIANTS[v][0] for v in variants} - set(cache))
    if needed:
        cache.update(decode_all(args.checkpoint, records, needed, args.workers))
        cache_path.write_text(json.dumps(cache))

    reports: dict[str, EvaluationReport] = {}
    if args.with_template:
        template = TemplateBaseline()
        predictions = template.predict_records(records)
        reports["template"] = _write(args.output_dir / "template", records, predictions)

    postprocessor = LSTMBaseline()
    for variant in variants:
        pass_name, repair, render = VARIANTS[variant]
        options = DecodeOptions(repair=repair, restore_surface_forms=render)
        predictions = tuple(
            Prediction(
                r.example_id,
                f"lstm-{variant}",
                postprocessor.postprocess(
                    cache[pass_name][r.example_id],
                    r.question,
                    r.schema_text,
                    r.database_id,
                    options,
                ),
            )
            for r in records
        )
        reports[variant] = _write(args.output_dir / variant, records, predictions)

    manifest: dict[str, object] = {
        "checkpoint": str(args.checkpoint),
        "dataset": args.dataset,
        "split": args.split,
        "limit": args.limit,
        "sample": args.sample,
        "passes": {name: asdict(PASSES[name]) for name in PASSES},
        "variants": {name: VARIANTS[name] for name in variants},
        "results": {},
    }
    results: dict[str, object] = manifest["results"]  # type: ignore[assignment]
    for name, report in reports.items():
        row = _summary(report)
        if args.dataset == "spider" and not args.no_official:
            row["official"] = _official(args.output_dir / name, args.split)
        for reference in ("template", "as_submitted"):
            if reference in reports and reference != name:
                test = mcnemar_exact(
                    [i.execution_match for i in report.examples],
                    [i.execution_match for i in reports[reference].examples],
                )
                row[f"mcnemar_execution_vs_{reference}"] = asdict(test)
        results[name] = row
        print(
            f"{name:16s} EX={row['execution_strict']['estimate']:.4f} "
            f"EXoff={row['execution_official_semantics']['estimate']:.4f} "
            f"SM={row['string_match']['estimate']:.4f} "
            f"invalid={row['invalid_sql']['estimate']:.4f}"
            + (
                f" officialEM={row['official']['exact_set_match']['all']:.3f}"
                f" officialEX={row['official']['execution']['all']:.3f}"
                if row.get("official")
                else ""
            ),
            flush=True,
        )
    (args.output_dir / "ablation_manifest.json").write_text(json.dumps(manifest, indent=2))
    return 0


def _write(
    directory: Path, records: tuple[ExampleRecord, ...], predictions: tuple[Prediction, ...]
) -> EvaluationReport:
    report = evaluate_predictions(records, predictions)
    write_prediction_artifacts(directory / "predictions.jsonl", records, predictions)
    write_evaluation_reports(directory, report, records)
    return report


if __name__ == "__main__":
    raise SystemExit(main())
