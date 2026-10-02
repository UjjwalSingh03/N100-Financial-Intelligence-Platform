import streamlit as st

from src.dashboard.utils.db import get_companies, get_pl, get_bs, get_cf

def render():
    st.title("Company Profile")
    companies = get_companies()
    if companies.empty:
        st.info("Database not available.")
        return
    ticker_col = next((c for c in ("ticker", "symbol") if c in companies.columns), None)
    if not ticker_col:
        st.error("Company ticker column is missing.")
        return
    ticker = st.selectbox("Company", sorted(companies[ticker_col].dropna().astype(str).unique()))
    row = companies[companies[ticker_col].astype(str) == ticker].iloc[0]
    st.json(row.to_dict())
    for title, loader in (("Profit & Loss", get_pl), ("Balance Sheet", get_bs), ("Cash Flow", get_cf)):
        with st.expander(title, expanded=title == "Profit & Loss"):
            data = loader(ticker)
            st.dataframe(data, use_container_width=True, hide_index=True) if not data.empty else st.info("No data available.")

