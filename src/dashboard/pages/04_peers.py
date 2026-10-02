"""Sprint 4 Day 24 — peer comparison."""
from __future__ import annotations
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from src.dashboard.utils.db import get_companies,get_peer_comparison,get_peer_groups,get_peer_radar

METRICS=["roe","roce","net_profit_margin","debt_to_equity","free_cash_flow","pat_cagr_5yr","revenue_cagr_5yr","eps_cagr_5yr"]
LABELS={"roe":"ROE","roce":"ROCE","net_profit_margin":"Net Profit Margin","debt_to_equity":"D/E","free_cash_flow":"FCF","pat_cagr_5yr":"PAT CAGR 5yr","revenue_cagr_5yr":"Revenue CAGR 5yr","eps_cagr_5yr":"EPS CAGR 5yr"}

def render():
    st.title("Peer Comparison")
    year=int(st.session_state.get("dashboard_year",2024))
    groups_df=get_peer_groups()
    if groups_df.empty or "peer_group_name" not in groups_df.columns:
        st.info("Peer groups are not available in db/nifty100.db.")
        return
    groups=sorted(groups_df["peer_group_name"].dropna().astype(str).unique())
    group=st.selectbox("Peer group",groups)
    data=get_peer_comparison(group,year)
    if data.empty:
        st.info(f"No peer data is available for {group} in {year}.")
        return

    companies=get_companies()
    ticker_col=next((c for c in ("ticker","symbol") if c in companies.columns),None)
    name_map=dict(zip(companies["id"],companies["company_name"]))
    ticker_map=dict(zip(companies["id"],companies[ticker_col])) if ticker_col else {}
    ids=sorted(data["company_id"].dropna().astype(str).unique())
    labels=[f"{name_map.get(int(cid),cid)} ({ticker_map.get(int(cid),'')})" for cid in ids]
    selected=st.selectbox("Benchmark company",labels)
    selected_id=ids[labels.index(selected)]
    selected_ticker=str(ticker_map.get(int(selected_id),""))

    radar=get_peer_radar(group,selected_ticker,year)
    if not radar.empty:
        theta=radar["metric"].tolist()
        company_vals=pd.to_numeric(radar["company"],errors="coerce").fillna(0).tolist()
        avg_vals=pd.to_numeric(radar["peer_average"],errors="coerce").fillna(0).tolist()
        fig=go.Figure()
        fig.add_trace(go.Scatterpolar(r=company_vals+[company_vals[0]],theta=theta+[theta[0]],fill="toself",name=selected))
        fig.add_trace(go.Scatterpolar(r=avg_vals+[avg_vals[0]],theta=theta+[theta[0]],fill="toself",name="Peer average"))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True)),title="Selected Company vs Peer Group Average")
        st.plotly_chart(fig,use_container_width=True)

    pivot=data.pivot_table(index=["company_id","company_name","ticker"],columns="metric",values="value",aggfunc="first").reset_index()
    metric_cols=[m for m in METRICS if m in pivot.columns]
    pivot=pivot[["company_id","company_name","ticker"]+metric_cols]
    pivot.columns=["company_id","company_name","ticker"]+[LABELS[m] for m in metric_cols]

    def highlight(row):
        return ["background-color: #fff2cc; font-weight: 600" if str(row["company_id"])==str(selected_id) else "" for _ in row]
    st.markdown("### Peer KPI comparison")
    st.dataframe(pivot.style.apply(highlight,axis=1),use_container_width=True,hide_index=True)
