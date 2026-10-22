"""Day 40 API smoke and parameter validation tests."""
from fastapi.testclient import TestClient
from src.api.main import app

def test_day40_openapi_routes():
    paths = app.openapi()["paths"]
    expected = ("/api/v1/screener", "/api/v1/sectors", "/api/v1/sectors/{sector}/companies",
                "/api/v1/peers/{group_name}", "/api/v1/companies/{ticker}/peers/compare",
                "/api/v1/market-cap/{ticker}", "/api/v1/portfolio/stats",
                "/api/v1/companies/{ticker}/documents")
    assert all(p in paths for p in expected)

def test_invalid_screener_filters_return_400():
    with TestClient(app) as client:
        for query in ("min_roe=bad", "max_de=-1", "max_pe=nan", "min_fcf=inf", "unexpected=3"):
            assert client.get("/api/v1/screener?" + query).status_code == 400

def test_export(tmp_path):
    from scripts.day40_export_api import export
    import json
    assert export(tmp_path) >= 16
    schema = json.loads((tmp_path / "openapi.json").read_text())
    collection = json.loads((tmp_path / "postman_collection.json").read_text())
    assert "/api/v1/screener" in schema["paths"]
    assert collection["item"]
