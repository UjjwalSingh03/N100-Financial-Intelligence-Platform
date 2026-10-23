import pytest

def test_min_roe(client):
    response=client.get("/api/v1/screener",params={"min_roe":15})
    assert response.status_code==200, response.text
    rows=response.json()
    assert rows, "Expected at least one company with ROE >= 15"
    assert all(isinstance(r.get("roe_pct"),(int,float)) and r["roe_pct"]>=15 for r in rows)
    ids={r["company_id"] for r in rows}
    assert len(ids)==len(rows)

@pytest.mark.parametrize("params",[{"min_roe":"invalid"},{"max_de":-1},{"max_pe":"nan"},{"min_fcf":"inf"}])
def test_invalid_screener_parameter(client,params):
    assert client.get("/api/v1/screener",params=params).status_code==400
