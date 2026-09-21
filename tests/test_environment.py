import sqlite3
import sys


def test_supported_runtime_and_sqlite() -> None:
    assert sys.version_info[:2] == (3, 12)
    connection = sqlite3.connect(":memory:")
    try:
        assert connection.execute("SELECT 1").fetchone() == (1,)
    finally:
        connection.close()
