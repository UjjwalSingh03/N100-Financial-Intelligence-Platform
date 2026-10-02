import streamlit as st

from src.dashboard.utils.db import get_companies, get_cf

def render():
    st.title("Capital Allocation")
    companies = get_companies()
    if companies.empty:
        st.info("Database not available.")
        return
    ticker_col = next((c for c in ("ticker", "symbol") if c in companies.columns), None)
    if not ticker_col:
        st.error("Company ticker column is missing.")
        return
    ticker = st.selectbox("Company", sorted(companies[ticker_col].dropna().astype(str).unique()))
    data = get_cf(ticker)
    st.dataframe(data, use_container_width=True, hide_index=True) if not data.empty else st.info("No cash-flow data available.")

