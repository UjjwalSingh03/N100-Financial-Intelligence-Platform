def test_eleven_sectors(client):
    response=client.get("/api/v1/sectors")
    assert response.status_code==200, response.text
    rows=response.json()
    assert len(rows)==11
    assert sum(r["company_count"] for r in rows)==92

def test_it_sector_only(client):
    response=client.get("/api/v1/sectors/IT/companies")
    assert response.status_code==200, response.text
    rows=response.json()
    assert rows and all(r["broad_sector"].casefold()=="it" for r in rows)

def test_unknown_sector(client):
    assert client.get("/api/v1/sectors/UNKNOWN_SECTOR/companies").status_code==404
