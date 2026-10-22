"""Read-only SQLite connections for API request handlers."""
import os
import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[2] / "db" / "nifty100.db"


def database_path() -> Path:
    return Path(os.getenv("N100_DB_PATH", str(DEFAULT_DB))).expanduser().resolve()


def get_connection():
    """Yield one connection per request; never silently create a missing database."""
    path = database_path()
    if not path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {path}")
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
    finally:
        con.close()
