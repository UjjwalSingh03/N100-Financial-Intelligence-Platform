from src.api.routers.health import CORE_TABLES

def test_health_status_and_counts(client):
    response=client.get("/api/v1/health")
    assert response.status_code==200, response.text
    data=response.json()
    assert data["status"]=="ok"
    assert set(data["db_row_counts"])==set(CORE_TABLES)
    assert data["db_row_counts"]["companies"]==92
    assert data["uptime_seconds"]>=0 and data["version"]
