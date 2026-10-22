"""Day 38 FastAPI scaffold contract tests."""
import sqlite3
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.routers.health import CORE_TABLES


def test_docs_and_openapi():
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 200
        spec = client.get("/openapi.json").json()
        assert "/api/v1/health" in spec["paths"]


def test_health_counts(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    with sqlite3.connect(db) as con:
        for table in CORE_TABLES:
            con.execute(f'CREATE TABLE "{table}" (id INTEGER PRIMARY KEY)')
        con.execute("INSERT INTO companies VALUES (1)")
    monkeypatch.setenv("N100_DB_PATH", str(db))
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db_row_counts"]["companies"] == 1
    assert len(data["db_row_counts"]) == 10
    assert data["uptime_seconds"] >= 0
    assert data["version"]


def test_missing_db_returns_503(tmp_path, monkeypatch):
    monkeypatch.setenv("N100_DB_PATH", str(tmp_path / "missing.db"))
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 503


def test_cors_preflight():
    with TestClient(app) as client:
        response = client.options("/api/v1/health", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
