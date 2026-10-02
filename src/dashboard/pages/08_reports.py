"""Sprint 4 Day 25 — annual reports."""
from __future__ import annotations
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
import streamlit as st
from src.dashboard.utils.db import get_companies,get_annual_reports

def _url_status(url):
    if not url:
        return False
    try:
        req=Request(str(url),method="HEAD",headers={"User-Agent":"Mozilla/5.0"})
        with urlopen(req,timeout=5) as resp:
            return int(getattr(resp,"status",200)) < 400
    except HTTPError as exc:
        return exc.code != 404 and exc.code < 400
    except (URLError,TimeoutError):
        return None

def render():
    st.title("Annual Reports")
    companies=get_companies()
    if companies.empty:
        st.info("Database not available.")
        return
    ticker_col=next((c for c in ("ticker","symbol") if c in companies.columns),None)
    if not ticker_col:
        st.error("Company ticker column is missing.")
        return
    query=st.text_input("Search company or ticker","")
    options=companies.copy()
    if query.strip():
        mask=options["company_name"].astype(str).str.contains(query.strip(),case=False,na=False)|options[ticker_col].astype(str).str.contains(query.strip(),case=False,na=False)
        options=options.loc[mask]
    if options.empty:
        st.warning("Company not found.")
        return
    labels=[f'{r["company_name"]} ({r[ticker_col]})' for _,r in options.iterrows()]
    selected=st.selectbox("Company",labels)
    ticker=str(options.iloc[labels.index(selected)][ticker_col])
    reports=get_annual_reports(ticker)
    if reports.empty:
        st.info("No annual-report documents are available for this company.")
        return
    for _,row in reports.iterrows():
        year=str(row.get("document_date") or "Year unavailable")
        url=row.get("document_url")
        status=_url_status(url)
        cols=st.columns([2,5,2])
        cols[0].write(f"**{year}**")
        if status is False:
            cols[1].markdown("Report unavailable")
            cols[2].markdown(":red[404 / unavailable]")
        elif status is None:
            if url:
                cols[1].markdown(f"[Open BSE PDF]({url})")
                cols[2].markdown(":orange[URL not verified]")
            else:
                cols[1].markdown("Report unavailable")
                cols[2].markdown(":red[No URL]")
        else:
            cols[1].markdown(f"[Open BSE PDF]({url})")
            cols[2].markdown(":green[Available]")
