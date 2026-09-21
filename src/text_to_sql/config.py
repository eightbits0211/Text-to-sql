"""Typed configuration for reproducible Part 2 runs."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Part2Config:
    wikisql_source: Path
    wikisql_database_root: Path
    spider_source: Path
    spider_schema: Path
    spider_database_root: Path
    artifact_directory: Path = Path("artifacts/part2")
    smoke_limit: int = 25

    @classmethod
    def from_environment(cls) -> "Part2Config":
        """Load paths from environment variables with no machine-specific defaults."""
        return cls(
            wikisql_source=_required_path("TEXT2SQL_WIKISQL_SOURCE"),
            wikisql_database_root=_required_path("TEXT2SQL_WIKISQL_DATABASE_ROOT"),
            spider_source=_required_path("TEXT2SQL_SPIDER_SOURCE"),
            spider_schema=_required_path("TEXT2SQL_SPIDER_SCHEMA"),
            spider_database_root=_required_path("TEXT2SQL_SPIDER_DATABASE_ROOT"),
            artifact_directory=Path(
                os.environ.get("TEXT2SQL_ARTIFACT_DIRECTORY", "artifacts/part2")
            ),
            smoke_limit=int(os.environ.get("TEXT2SQL_SMOKE_LIMIT", "25")),
        )

    def validate(self) -> None:
        if self.smoke_limit < 0:
            raise ValueError("smoke_limit must be non-negative")
        required = (
            self.wikisql_source,
            self.wikisql_database_root,
            self.spider_source,
            self.spider_schema,
            self.spider_database_root,
        )
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise FileNotFoundError("Configured dataset paths do not exist: " + ", ".join(missing))


def _required_path(variable: str) -> Path:
    value = os.environ.get(variable)
    if not value:
        raise ValueError(f"Set required environment variable: {variable}")
    return Path(value).expanduser()
