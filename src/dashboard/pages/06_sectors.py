import streamlit as st

from src.dashboard.utils.db import get_sectors

def render():
    st.title("Sector Analysis")
    data = get_sectors()
    if data.empty:
        st.info("Sector table is not available.")
        return
    st.dataframe(data, use_container_width=True, hide_index=True)

