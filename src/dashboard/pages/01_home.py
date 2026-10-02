import streamlit as st

from src.dashboard.utils.db import get_companies

def render():
    st.title("Nifty 100 Analytics")
    st.subheader("Home")
    companies = get_companies()
    if companies.empty:
        st.info("Add or generate db/nifty100.db to load the 92-company dashboard.")
        return
    st.metric("Companies", len(companies))
    st.dataframe(companies, use_container_width=True, hide_index=True)

