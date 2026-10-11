"""Show what preprocessing does to one example, plus corpus-level statistics.

Runs the real pipeline (loader -> schema serialisation -> tokenisation ->
vocabulary lookup -> copy-target resolution) so its output can be quoted in
the report and shown live in the viva.

Usage:
    uv run python -m scripts.show_preprocessing                     # spider-dev-4 + statistics
    uv run python -m scripts.show_preprocessing --example spider-dev-20 --no-stats
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

from text_to_sql.data.contracts import DatasetSplit, ExampleRecord
from text_to_sql.data.spider import load_spider
from text_to_sql.lstm.preprocessing import (
    FixedVocabulary,
    build_copy_target,
    resolve_target_token,
    tokenize_example,
)

_SPIDER = Path("/Users/roshini/datasets/text-to-sql/spider/spider_data")
_VOCAB = Path(
    "/Users/roshini/datasets/text-to-sql/artifacts-lstm-gpu-run/lstm-checkpoint/vocabulary.json"
)


def load_vocabulary(path: Path) -> FixedVocabulary:
    payload = json.loads(path.read_text(encoding="utf-8"))
    tokens = tuple(payload["tokens"])
    return FixedVocabulary(tokens, {t: i for i, t in enumerate(tokens)}, {})


def show_example(record: ExampleRecord, vocabulary: FixedVocabulary) -> None:
    tokenized = tokenize_example(record)
    copy_target = build_copy_target(record, vocabulary)
    print(f"Example {record.example_id} ({record.database_id}, {record.difficulty.value})")
    print(f"\n1. Raw question:\n   {record.question}")
    print(
        f"\n2. Question tokens ({len(tokenized.question_tokens)}):\n   {list(tokenized.question_tokens)}"
    )
    schema_lines = record.schema_text.splitlines()
    print(f"\n3. Serialised schema ({len(schema_lines)} lines; first 12 shown):")
    for line in schema_lines[:12]:
        print(f"   {line}")
    print(
        f"\n4. Encoder input: <bos> question <schema_sep> schema <eos> = "
        f"{len(tokenized.encoder_tokens)} tokens; first 20:\n   {list(tokenized.encoder_tokens[:20])}"
    )
    print(f"\n5. Gold SQL:\n   {record.gold_sql}")
    print("\n6. Target tokens and how each is produced (vocab = generate, copy = point to input):")
    rows = []
    for token in tokenized.sql_tokens:
        resolved = resolve_target_token(token, vocabulary, copy_target)
        kind = (
            "unk"
            if resolved.event is not None
            else ("vocab" if resolved.index < len(vocabulary) else "copy")
        )
        rows.append(f"{token}[{kind}]")
    print("   " + " ".join(rows))
    print(
        f"\n   Extended vocabulary for this example: {len(vocabulary):,} fixed + "
        f"{len(copy_target.copy_index_by_token)} copy-only source tokens"
    )


def corpus_statistics(
    name: str, records: tuple[ExampleRecord, ...], vocabulary: FixedVocabulary
) -> dict[str, object]:
    q_len, sql_len, enc_len, tables, columns = [], [], [], [], []
    kinds: Counter[str] = Counter()
    for record in records:
        tokenized = tokenize_example(record)
        q_len.append(len(tokenized.question_tokens))
        sql_len.append(len(tokenized.sql_tokens))
        enc_len.append(len(tokenized.encoder_tokens))
        tables.append(record.schema_text.count("\ntable: "))
        columns.append(record.schema_text.count("\n  - ") - record.schema_text.count(" -> "))
        copy_target = build_copy_target(record, vocabulary)
        for token in tokenized.sql_tokens:
            resolved = resolve_target_token(token, vocabulary, copy_target)
            if resolved.event is not None:
                kinds["unk"] += 1
            elif resolved.index < len(vocabulary):
                kinds["vocab"] += 1
            else:
                kinds["copy"] += 1
    total = sum(kinds.values())
    return {
        "split": name,
        "examples": len(records),
        "databases": len({r.database_id for r in records}),
        "question_tokens_mean": statistics.mean(q_len),
        "sql_tokens_mean": statistics.mean(sql_len),
        "encoder_tokens_mean": statistics.mean(enc_len),
        "encoder_tokens_max": max(enc_len),
        "encoder_over_256": sum(length > 256 for length in enc_len),
        "tables_per_schema_mean": statistics.mean(tables),
        "columns_per_schema_mean": statistics.mean(columns),
        "target_token_share": {k: kinds[k] / total for k in ("vocab", "copy", "unk")},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--example", default="spider-dev-4")
    parser.add_argument("--no-stats", action="store_true")
    parser.add_argument("--output", type=Path, default=None, help="Write statistics JSON here")
    args = parser.parse_args()

    vocabulary = load_vocabulary(_VOCAB)
    splits = {
        "train": load_spider(
            _SPIDER / "train_spider.json",
            _SPIDER / "tables.json",
            _SPIDER / "database",
            split=DatasetSplit.TRAIN,
        ).records,
        "dev": load_spider(
            _SPIDER / "dev.json",
            _SPIDER / "tables.json",
            _SPIDER / "database",
            split=DatasetSplit.DEV,
        ).records,
        "test": load_spider(
            _SPIDER / "test.json",
            _SPIDER / "test_tables.json",
            _SPIDER / "test_database",
            split=DatasetSplit.TEST,
        ).records,
    }
    by_id = {r.example_id: r for records in splits.values() for r in records}
    show_example(by_id[args.example], vocabulary)
    if args.no_stats:
        return 0
    stats = [corpus_statistics(name, records, vocabulary) for name, records in splits.items()]
    print("\nCorpus statistics (Spider, tokenised as the model sees it):")
    for row in stats:
        share = row["target_token_share"]
        print(
            f"  {row['split']:<5} n={row['examples']:>5} dbs={row['databases']:>3} "
            f"q={row['question_tokens_mean']:.1f} sql={row['sql_tokens_mean']:.1f} "
            f"enc={row['encoder_tokens_mean']:.0f} (max {row['encoder_tokens_max']}, "
            f">256: {row['encoder_over_256']}) tables={row['tables_per_schema_mean']:.1f} "
            f"cols={row['columns_per_schema_mean']:.1f} | target: vocab {share['vocab']:.1%} "
            f"copy {share['copy']:.1%} unk {share['unk']:.1%}"
        )
    if args.output:
        args.output.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
