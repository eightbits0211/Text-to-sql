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

## Sources and verification

Use the official WikiSQL and Spider releases or course-approved mirrors.
Record the download URL, release/version, local file checksums, and any
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
