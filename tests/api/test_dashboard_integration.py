"""Verify the Streamlit API adapter and API endpoint return identical screener companies."""
import httpx
from src.dashboard.utils.api import api_screener, api_screener_ids

def test_dashboard_api_screener_parity(client):
    thresholds={"roe_min":15.0,"de_max":2.0}
    direct=client.get("/api/v1/screener",params={"min_roe":15.0,"max_de":2.0})
    assert direct.status_code==200, direct.text
    def forward(request):
        result=client.get(request.url.path,params=dict(request.url.params))
        return httpx.Response(result.status_code, json=result.json())
    transport=httpx.MockTransport(forward)
    frame=api_screener(thresholds,base_url="http://testserver",transport=transport)
    expected={r["company_id"] for r in direct.json()}
    assert set(frame["company_id"].astype(str))==expected if not frame.empty else expected==set()
    assert api_screener_ids(thresholds,base_url="http://testserver",transport=transport)==expected
