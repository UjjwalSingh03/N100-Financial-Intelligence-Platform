def test_company_directory_has_92(client):
    response=client.get("/api/v1/companies")
    assert response.status_code==200, response.text
    rows=response.json()
    assert len(rows)==92 and len({r["id"] for r in rows})==92

def test_tcs_profile(client):
    response=client.get("/api/v1/companies/TCS")
    assert response.status_code==200, response.text
    data=response.json()
    assert data["id"].upper()=="TCS"
    assert "Tata Consultancy" in data["company_name"]
    assert "latest_year_kpis" in data and "broad_sector" in data

def test_unknown_company(client):
    assert client.get("/api/v1/companies/INVALID").status_code==404
