"""Sprint 4 Day 25 — trend analysis."""
from __future__ import annotations
import plotly.graph_objects as go
import streamlit as st
from src.dashboard.utils.db import get_companies, get_trend_data

METRICS=["ROE","ROCE","Net Profit Margin","Operating Profit Margin","D/E","FCF","Revenue CAGR 5yr","PAT CAGR 5yr","EPS CAGR 5yr","Composite Score"]

def render():
    st.title("Trend Analysis")
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
    metrics=st.multiselect("Metrics (up to 3)",METRICS,default=["ROE"],max_selections=3)
    if not metrics:
        st.info("Select at least one metric.")
        return
    data=get_trend_data(ticker,tuple(metrics))
    if data.empty:
        st.info("No trend history available.")
        return
    fig=go.Figure()
    for metric in metrics:
        y=data[metric]
        yoy=y.pct_change().mul(100)
        yoy_text=[f"{v:+.1f}%" if v==v else "—" for v in yoy]
        fig.add_trace(go.Scatter(
            x=data["year"], y=y, mode="lines+markers+text", name=metric,
            text=yoy_text, textposition="top center",
            hovertemplate=f"%{{x}}<br>{metric}: %{{y:.2f}}<br>YoY: %{{text}}<extra></extra>",
        ))
    fig.update_layout(
        title="10-Year Financial Trends with YoY % Change",
        xaxis_title="Year", hovermode="x unified",
    )
    st.plotly_chart(fig,use_container_width=True)
