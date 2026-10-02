"""Sprint 4 Day 25 — capital allocation map."""
from __future__ import annotations
import plotly.express as px
import streamlit as st
from src.dashboard.utils.db import get_capital_allocation

def render():
    st.title("Capital Allocation Map")
    year=int(st.session_state.get("dashboard_year",2024))
    data=get_capital_allocation(year)
    if data.empty:
        st.info("Capital-allocation data is not available.")
        return
    counts=data.groupby("pattern",dropna=False).size().reset_index(name="companies")
    fig=px.treemap(counts,path=["pattern"],values="companies",title=f"Capital Allocation Patterns — {year}")
    fig.update_traces(textinfo="label+value")
    event=st.plotly_chart(fig,use_container_width=True,on_select="rerun",selection_mode=["points"])
    pattern=None
    if event and getattr(event,"selection",None):
        points=event.selection.get("points",[])
        if points:
            pattern=points[0].get("label")
    st.caption("Click a pattern in the treemap to view its companies.")
    if pattern and pattern in set(data["pattern"]):
        st.subheader(f"{pattern} — Companies")
        cols=["company_id","company_name","ticker"]
        st.dataframe(data.loc[data["pattern"]==pattern,cols].sort_values("company_name"),use_container_width=True,hide_index=True)
    else:
        st.markdown("### All pattern counts")
        st.dataframe(counts.sort_values("companies",ascending=False),use_container_width=True,hide_index=True)
