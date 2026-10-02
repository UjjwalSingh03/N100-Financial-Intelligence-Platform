"""Sprint 4 Day 25 — sector analysis."""
from __future__ import annotations
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.dashboard.utils.db import get_sector_analysis,get_sector_groups

def render():
    st.title("Sector Analysis")
    year=int(st.session_state.get("dashboard_year",2024))
    groups=get_sector_groups()
    if groups.empty:
        st.info("Sector data is not available.")
        return
    sectors=groups["sector"].dropna().astype(str).tolist()
    sector=st.selectbox("Sector",sectors)
    data=get_sector_analysis(sector,year).copy()
    if data.empty:
        st.info(f"No data available for {sector} in {year}.")
        return
    for c in ("revenue","roe","market_cap"):
        data[c]=__import__("pandas").to_numeric(data[c],errors="coerce")
    data=data.dropna(subset=["revenue","roe"]).copy()
    if data.empty:
        st.info("Revenue/ROE data is unavailable for this sector.")
        return
    data["market_cap"]=data["market_cap"].fillna(0).clip(lower=0)
    data["bubble_size"]=data["market_cap"].replace(0,1)
    fig=px.scatter(data,x="revenue",y="roe",size="bubble_size",color="sub_sector",hover_name="company_name",hover_data={"ticker":True,"market_cap":":,.0f","bubble_size":False},title=f"{sector} — Revenue vs ROE ({year})",size_max=55)
    fig.update_layout(xaxis_title="Revenue",yaxis_title="ROE (%)")
    st.plotly_chart(fig,use_container_width=True)
    med=data[["revenue","roe","market_cap"]].median(numeric_only=True)
    kpi=__import__("pandas").DataFrame({"Metric":["Revenue","ROE","Market Cap"],"Median":[med["revenue"],med["roe"],med["market_cap"]]})
    bar=go.Figure(go.Bar(x=kpi["Metric"],y=kpi["Median"],text=kpi["Median"].round(2),textposition="outside"))
    bar.update_layout(title="Sector Median KPIs",yaxis_title="Median value")
    st.plotly_chart(bar,use_container_width=True)
