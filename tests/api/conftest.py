"""Day 42 production API tests. Set N100_DB_PATH to the loaded 92-company SQLite DB."""
import os
import sqlite3
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.routers.health import CORE_TABLES

@pytest.fixture(scope="module")
def production_db():
    path=Path(os.getenv("N100_DB_PATH", "db/nifty100.db"))
    if not path.is_file():
        pytest.fail(f"Day 42 production integration requires loaded database: {path}")
    with sqlite3.connect(path) as con:
        count=con.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    assert count==92, f"Expected 92 companies, got {count}"
    return path

@pytest.fixture
def client(production_db, monkeypatch):
    monkeypatch.setenv("N100_DB_PATH",str(production_db.resolve()))
    with TestClient(app) as test_client:
        yield test_client
