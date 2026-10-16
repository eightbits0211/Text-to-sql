import sqlite3
from pathlib import Path

from text_to_sql.data.contracts import DatasetSplit, ExampleRecord, QueryDifficulty, QueryStructure
from text_to_sql.llm.gpt_adapter import final_answer
from text_to_sql.llm.prompts import FewShotSelector, build_messages, extract_sql


def _db(tmp_path: Path) -> Path:
    path = tmp_path / "shop.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT)")
        connection.execute(
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER "
            "REFERENCES customers(id))"
        )
        connection.execute("INSERT INTO customers VALUES (1, 'Ada')")
    return path


def _record(path: Path, db: str, question: str, index: int = 0) -> ExampleRecord:
    return ExampleRecord(
        example_id=f"{db}-{index}",
        dataset="fixture",
        split=DatasetSplit.DEV,
        database_id=db,
        database_path=path,
        question=question,
        schema_text="database: x\ntable: t\ncolumns:\n  - c [TEXT]",
        gold_sql="SELECT count(*) FROM customers",
        difficulty=QueryDifficulty.EASY,
        query_structure=QueryStructure.SINGLE_TABLE,
    )


def test_prompt_has_create_table_keys_and_sample_rows(tmp_path):
    messages = build_messages(_record(_db(tmp_path), "shop", "How many customers?"))
    user = messages[-1]["content"]
    assert 'CREATE TABLE "customers"' in user
    assert 'PRIMARY KEY ("id")' in user
    assert 'FOREIGN KEY ("customer_id") REFERENCES "customers"("id")' in user
    assert "1 | Ada" in user
    assert user.endswith("Question: How many customers?")


def test_few_shot_excludes_target_database_and_ranks_by_similarity(tmp_path):
    path = _db(tmp_path)
    pool = [
        _record(path, "shop", "How many customers are there?", 0),
        _record(path, "zoo", "How many animals are there?", 1),
        _record(path, "zoo", "List all keepers by salary", 2),
    ]
    target = _record(path, "shop", "How many orders are there?", 9)
    chosen = FewShotSelector(pool).select(target, 1)
    assert [ex.example_id for ex in chosen] == ["zoo-1"]


def test_extract_sql_and_final_channel():
    assert extract_sql("Sure:\n```sql\nSELECT name\nFROM t;\n```") == "SELECT name FROM t"
    assert extract_sql("The answer is SELECT 1;") == "SELECT 1"
    assert extract_sql("no sql here") == ""
    raw = "<|channel|>analysis<|message|>think<|end|><|start|>assistant<|channel|>final<|message|>```sql\nSELECT 1\n```<|return|>"
    assert final_answer(raw) == "```sql\nSELECT 1\n```"
