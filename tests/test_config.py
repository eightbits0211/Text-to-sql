from pathlib import Path

import pytest

from text_to_sql.config import Part2Config


def test_config_reads_dataset_paths_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "TEXT2SQL_WIKISQL_SOURCE": "wiki.json",
        "TEXT2SQL_WIKISQL_DATABASE_ROOT": "wiki-db",
        "TEXT2SQL_SPIDER_SOURCE": "spider.json",
        "TEXT2SQL_SPIDER_SCHEMA": "tables.json",
        "TEXT2SQL_SPIDER_DATABASE_ROOT": "spider-db",
        "TEXT2SQL_SMOKE_LIMIT": "3",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)

    config = Part2Config.from_environment()

    assert config.wikisql_source == Path("wiki.json")
    assert config.spider_database_root == Path("spider-db")
    assert config.smoke_limit == 3


def test_config_reports_missing_paths(tmp_path: Path) -> None:
    config = Part2Config(
        wikisql_source=tmp_path / "missing-wiki.json",
        wikisql_database_root=tmp_path / "missing-wiki-db",
        spider_source=tmp_path / "missing-spider.json",
        spider_schema=tmp_path / "missing-tables.json",
        spider_database_root=tmp_path / "missing-spider-db",
    )

    with pytest.raises(FileNotFoundError, match="Configured dataset paths"):
        config.validate()
