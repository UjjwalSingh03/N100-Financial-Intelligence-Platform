"""Optional Streamlit API-backed screener; shared by UI and parity test."""
import os
import httpx
import pandas as pd

API_FILTERS = {"roe_min":"min_roe","de_max":"max_de","fcf_min":"min_fcf",
               "revenue_cagr_5yr_min":"min_rev_cagr_5yr",
               "pat_cagr_5yr_min":"min_pat_cagr_5yr","pe_max":"max_pe"}

def api_screener(thresholds=None, *, base_url=None, transport=None):
    base_url=(base_url or os.getenv("N100_API_URL","http://127.0.0.1:8000")).rstrip("/")
    params={API_FILTERS[k]:v for k,v in (thresholds or {}).items() if k in API_FILTERS and v is not None}
    with httpx.Client(base_url=base_url, transport=transport, timeout=15) as client:
        response=client.get("/api/v1/screener",params=params)
        response.raise_for_status()
        return pd.DataFrame(response.json())

def api_screener_ids(thresholds=None, **kwargs):
    data=api_screener(thresholds,**kwargs)
    return set(data["company_id"].astype(str)) if "company_id" in data else set()
