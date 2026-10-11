"""Per-question official Spider scores (exact-set match and execution).

Run with the evaluator's own interpreter, from inside the evaluator checkout
(``taoyds/test-suite-sql-eval``), so its modules import unchanged:

    cd <evaluator> && <evalenv>/bin/python <repo>/scripts/official_per_example.py \
        gold.txt pred.txt <db_dir> <tables.json> out.jsonl

It mirrors the scoring loop of the official ``evaluation.py`` (no value
plugging, DISTINCT not kept) but writes one JSON line per question, so paired
tests and clustered bootstraps can be run on the official metrics.
"""

import json
import os
import sys

sys.path.insert(0, os.getcwd())  # the evaluator checkout (run from inside it)

from evaluation import (
    Evaluator,
    Schema,
    build_foreign_key_map_from_json,
    build_valid_col_units,
    get_schema,
    get_sql,
    rebuild_sql_col,
    rebuild_sql_val,
)
from exec_eval import eval_exec_match

_EMPTY_SQL = {
    "except": None,
    "from": {"conds": [], "table_units": []},
    "groupBy": [],
    "having": [],
    "intersect": None,
    "limit": None,
    "orderBy": [],
    "select": [False, []],
    "union": None,
    "where": [],
}


def main() -> int:
    gold_path, pred_path, db_dir, table_path, out_path = sys.argv[1:6]
    kmaps = build_foreign_key_map_from_json(table_path)
    evaluator = Evaluator()
    with open(gold_path) as gold_file, open(pred_path) as pred_file:
        gold = [line.rstrip("\n").split("\t") for line in gold_file if line.strip()]
        pred = [line.rstrip("\n") for line in pred_file if line.strip()]
    assert len(gold) == len(pred), "gold/pred length mismatch"
    with open(out_path, "w") as out:
        for index, ((g_str, db_name), p_str) in enumerate(zip(gold, pred)):
            p_str = p_str.replace("value", "1")
            db = os.path.join(db_dir, db_name, db_name + ".sqlite")
            schema = Schema(get_schema(db))
            g_sql = get_sql(schema, g_str)
            hardness = evaluator.eval_hardness(g_sql)
            try:
                p_sql = get_sql(schema, p_str)
            except Exception:  # noqa: BLE001 - the official script treats any parse failure as empty SQL
                p_sql = json.loads(json.dumps(_EMPTY_SQL))
            exec_score = eval_exec_match(
                db=db,
                p_str=p_str,
                g_str=g_str,
                plug_value=False,
                keep_distinct=False,
                progress_bar_for_each_datapoint=False,
            )
            kmap = kmaps[db_name]
            g_valid = build_valid_col_units(g_sql["from"]["table_units"], schema)
            g_sql = rebuild_sql_col(g_valid, rebuild_sql_val(g_sql), kmap)
            p_valid = build_valid_col_units(p_sql["from"]["table_units"], schema)
            p_sql = rebuild_sql_col(p_valid, rebuild_sql_val(p_sql), kmap)
            exact = evaluator.eval_exact_match(p_sql, g_sql)
            out.write(
                json.dumps(
                    {
                        "index": index,
                        "db_id": db_name,
                        "hardness": hardness,
                        "exec": int(bool(exec_score)),
                        "exact": int(bool(exact)),
                    }
                )
                + "\n"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
