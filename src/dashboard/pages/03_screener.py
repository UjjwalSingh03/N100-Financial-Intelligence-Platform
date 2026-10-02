import io
import streamlit as st

from src.dashboard.utils.db import get_companies, get_ratios

def render():
    st.title("Screener")
    companies = get_companies()
    if companies.empty:
        st.info("Database not available.")
        return
    ticker_col = next((c for c in ("ticker", "symbol") if c in companies.columns), None)
    if not ticker_col:
        st.error("Company ticker column is missing.")
        return
    tickers = sorted(companies[ticker_col].dropna().astype(str).unique())
    ticker = st.selectbox("Preview company", tickers)
    data = get_ratios(ticker)
    st.dataframe(data, use_container_width=True, hide_index=True)
    if not data.empty:
        st.download_button("Download CSV", data.to_csv(index=False).encode(), f"{ticker}_screener.csv", "text/csv")

