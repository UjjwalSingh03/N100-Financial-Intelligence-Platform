import streamlit as st

from src.dashboard.utils.db import get_companies, get_ratios

def render():
    st.title("Trends")
    companies = get_companies()
    if companies.empty:
        st.info("Database not available.")
        return
    ticker_col = next((c for c in ("ticker", "symbol") if c in companies.columns), None)
    if not ticker_col:
        st.error("Company ticker column is missing.")
        return
    ticker = st.selectbox("Company", sorted(companies[ticker_col].dropna().astype(str).unique()))
    data = get_ratios(ticker)
    if data.empty:
        st.info("No ratio history available.")
        return
    st.line_chart(data.set_index("year") if "year" in data.columns else data.select_dtypes("number"))

