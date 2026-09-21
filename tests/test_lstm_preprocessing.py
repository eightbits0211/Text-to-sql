from pathlib import Path

from text_to_sql.data.contracts import (
    DatasetSplit,
    ExampleRecord,
    QueryDifficulty,
    QueryStructure,
)
from text_to_sql.lstm.preprocessing import (
    build_copy_target,
    build_training_vocabulary,
    resolve_target_token,
    tokenize_question,
    tokenize_schema,
    tokenize_sql,
)


def _example(
    *,
    example_id: str,
    question: str,
    schema_text: str,
    gold_sql: str,
    split: DatasetSplit,
    source_index: int | None = None,
) -> ExampleRecord:
    return ExampleRecord(
        example_id=example_id,
        dataset="wikisql",
        split=split,
        database_id="db_1",
        database_path=Path("/tmp/db_1.sqlite"),
        question=question,
        schema_text=schema_text,
        gold_sql=gold_sql,
        difficulty=QueryDifficulty.EASY,
        query_structure=QueryStructure.SINGLE_TABLE,
        source_index=source_index,
    )


def test_questions_sql_and_schema_tokenization_is_deterministic() -> None:
    question = "Which singer names are from the United States?"
    schema_text = "database: music\ntable: singers\ncolumns:\n  - singer_id [INTEGER]\n  - name [TEXT]"
    sql = "SELECT name FROM singers WHERE singer_id = 7;"

    assert tokenize_question(question) == [
        "which",
        "singer",
        "names",
        "are",
        "from",
        "the",
        "united",
        "states",
    ]
    assert tokenize_schema(schema_text) == [
        "database",
        "music",
        "table",
        "singers",
        "columns",
        "singer_id",
        "integer",
        "name",
        "text",
    ]
    assert tokenize_sql(sql) == [
        "SELECT",
        "name",
        "FROM",
        "singers",
        "WHERE",
        "singer_id",
        "=",
        "7",
        ";",
    ]


def test_training_vocabulary_is_train_only_and_dev_does_not_expand_it() -> None:
    train_example = _example(
        example_id="train_1",
        question="Which names are in the train table?",
        schema_text="database: demo\ntable: train_table\ncolumns:\n  - train_id [INTEGER]\n  - name [TEXT]",
        gold_sql="SELECT name FROM train_table WHERE train_id = 1;",
        split=DatasetSplit.TRAIN,
    )
    dev_example = _example(
        example_id="dev_1",
        question="Which dev_only_name values are present?",
        schema_text="database: demo\ntable: dev_table\ncolumns:\n  - dev_only_name [TEXT]",
        gold_sql="SELECT dev_only_name FROM dev_table;",
        split=DatasetSplit.DEV,
    )

    vocab = build_training_vocabulary((train_example, dev_example))

    assert "train_id" in vocab
    assert "dev_only_name" not in vocab
    assert "<unk>" in vocab
    assert "SELECT" in vocab


def test_unseen_source_identifier_builds_copy_target() -> None:
    example = _example(
        example_id="copy_1",
        question="Which rows include Foo_Bar?",
        schema_text="database: demo\ntable: artists\ncolumns:\n  - artist_id [INTEGER]\n  - name [TEXT]",
        gold_sql="SELECT name FROM artists WHERE name = 'Foo_Bar';",
        split=DatasetSplit.DEV,
    )
    vocab = build_training_vocabulary((example,))
    copy_target = build_copy_target(example, vocab)

    assert "foo_bar" in copy_target.copy_index_by_token
    assert copy_target.source_tokens[3] == "Foo_Bar"
    assert copy_target.source_positions["foo_bar"] == (3,)
    assert copy_target.source_to_index["foo_bar"] == copy_target.copy_index_by_token["foo_bar"]
    assert "Foo_Bar" in copy_target.extended_tokens

    resolution = resolve_target_token("Foo_Bar", vocab, copy_target)
    assert resolution.index == copy_target.copy_index_by_token["foo_bar"]
    assert copy_target.extended_tokens[resolution.index] == "Foo_Bar"


def test_fixed_vocabulary_takes_precedence_over_copy_target() -> None:
    train_example = _example(
        example_id="train_2",
        question="Which names are there?",
        schema_text="database: demo\ntable: people\ncolumns:\n  - id [INTEGER]\n  - name [TEXT]",
        gold_sql="SELECT name FROM people;",
        split=DatasetSplit.TRAIN,
    )
    vocab = build_training_vocabulary((train_example,))
    example = _example(
        example_id="copy_2",
        question="What is the Name of the person?",
        schema_text="database: demo\ntable: people\ncolumns:\n  - id [INTEGER]\n  - name [TEXT]",
        gold_sql="SELECT Name FROM people;",
        split=DatasetSplit.DEV,
    )
    copy_target = build_copy_target(example, vocab)

    assert "name" in vocab
    assert copy_target.source_to_index["name"] == vocab.token_to_index["name"]
    assert resolve_target_token("Name", vocab, copy_target).index == vocab.token_to_index["name"]


def test_duplicate_source_token_has_a_single_mapping() -> None:
    example = _example(
        example_id="copy_3",
        question="Return the name name value.",
        schema_text="database: demo\ntable: names\ncolumns:\n  - name [TEXT]",
        gold_sql="SELECT name FROM names;",
        split=DatasetSplit.TRAIN,
    )
    vocab = build_training_vocabulary((example,))
    copy_target = build_copy_target(example, vocab)

    assert copy_target.source_positions["name"] == (2, 3, 10)
    assert copy_target.source_to_index["name"] == vocab.token_to_index["name"]


def test_unresolvable_target_records_explicit_event() -> None:
    example = _example(
        example_id="copy_4",
        question="Who has unseen_identifier?",
        schema_text="database: demo\ntable: artists\ncolumns:\n  - id [INTEGER]",
        gold_sql="SELECT id FROM artists;",
        split=DatasetSplit.TRAIN,
    )
    vocab = build_training_vocabulary((example,))
    copy_target = build_copy_target(example, vocab)
    resolution = resolve_target_token("never_seen_identifier", vocab, copy_target)

    assert resolution.token == "<unk>"
    assert resolution.event is not None
    assert resolution.event.reason == "unresolvable_target_token"
    assert resolution.event.normalized == "never_seen_identifier"
    assert resolution.index == vocab.token_to_index["<unk>"]


def test_duplicate_unseen_source_token_shares_single_copy_index() -> None:
    example = _example(
        example_id="copy_5",
        question="Find tag_x and tag_x.",
        schema_text="database: demo\ntable: items\ncolumns:\n  - id [INTEGER]",
        gold_sql="SELECT id FROM items;",
        split=DatasetSplit.DEV,
    )
    vocab = build_training_vocabulary((example,))
    copy_target = build_copy_target(example, vocab)

    assert copy_target.source_positions["tag_x"] == (1, 3)
    assert "tag_x" in copy_target.copy_index_by_token
    assert copy_target.source_to_index["tag_x"] == copy_target.copy_index_by_token["tag_x"]
    assert copy_target.extended_tokens.count("tag_x") == 1
