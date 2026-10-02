import streamlit as st

from src.dashboard.utils.db import get_peers, get_companies

def render():
    st.title("Peer Comparison")
    peers = get_peers("")
    if peers.empty:
        st.info("peer_percentiles is not available yet.")
        return
    groups = sorted(peers["peer_group_name"].dropna().astype(str).unique()) if "peer_group_name" in peers.columns else []
    if not groups:
        st.info("No peer groups available.")
        return
    group = st.selectbox("Peer group", groups)
    data = get_peers(group)
    st.dataframe(data, use_container_width=True, hide_index=True)

