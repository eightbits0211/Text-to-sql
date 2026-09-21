# Dataset setup

Datasets are not committed to this repository. Store them outside Git and
point the smoke runner at local paths through environment variables.

## Required layout

Set the following variables:

```bash
export TEXT2SQL_WIKISQL_SOURCE=/path/to/dev.json
export TEXT2SQL_WIKISQL_DATABASE_ROOT=/path/to/wikisql/databases
export TEXT2SQL_SPIDER_SOURCE=/path/to/dev.json
export TEXT2SQL_SPIDER_SCHEMA=/path/to/tables.json
export TEXT2SQL_SPIDER_DATABASE_ROOT=/path/to/spider/database
export TEXT2SQL_ARTIFACT_DIRECTORY=artifacts/part2
export TEXT2SQL_SMOKE_LIMIT=25
```

WikiSQL database filenames must match `{database_id}.db` by default. Spider
database files must match `{database_id}/{database_id}.sqlite` by default.
These patterns are configurable when calling the loaders directly.
For the official WikiSQL archive, point `TEXT2SQL_WIKISQL_SOURCE` to
`dev.jsonl`; the smoke runner automatically uses the adjacent
`dev.tables.jsonl` metadata file and `dev.db` database.

## Sources and verification

Recommended official sources:

- WikiSQL repository and release archive:
  <https://github.com/salesforce/WikiSQL>
- WikiSQL paper/citation: Zhong, Xiong, and Socher, *Seq2SQL*,
  <https://arxiv.org/abs/1709.00103>
- Spider dataset page and download:
  <https://yale-lily.github.io/spider>
- Spider scripts and evaluation repository:
  <https://github.com/taoyds/spider>
- Spider paper/citation: Yu et al., *Spider*,
  <https://arxiv.org/abs/1809.08887>

The WikiSQL repository identifies its code/data release with the BSD-3-Clause
license. The Spider dataset page identifies the dataset distribution as
CC BY-SA 4.0; this is distinct from the license of the Spider helper-code
repository. Confirm course policy before redistribution.

Record the exact download URL, release/version, local file checksums, and any
preprocessing in the experiment run manifest. Do not commit downloaded files,
credentials, or private benchmark labels.

## Smoke command

After all variables point to existing paths:

```bash
uv run python scripts/run_part2_smoke.py
```

The command writes predictions and JSON/CSV/Markdown evaluation reports under
`TEXT2SQL_ARTIFACT_DIRECTORY`. It exits before evaluation if a configured path
is missing, rather than silently reporting an empty benchmark.
