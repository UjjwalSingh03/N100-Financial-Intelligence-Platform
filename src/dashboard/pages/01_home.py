"""Sprint 4 Day 23 — Home dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_home_snapshot


def _fmt(value, suffix=""):
    if pd.isna(value):
        return "N/A"
    return f"{value:.2f}{suffix}"


def render():
    st.title("Nifty 100 Analytics")
    st.subheader("Home")

    year = int(st.session_state.get("dashboard_year", 2024))
    data = get_home_snapshot(year)

    if data.empty:
        st.info("Database not available. Add db/nifty100.db and reload the dashboard.")
        return

    # get_home_snapshot exposes normalized dashboard aliases rather than raw
    # source-table column names. Keep the page coupled to those stable names.
    roe = pd.to_numeric(data.get("roe"), errors="coerce")
    pe = pd.to_numeric(data.get("pe_ratio"), errors="coerce")
    de = pd.to_numeric(data.get("de"), errors="coerce")
    cagr = pd.to_numeric(data.get("revenue_cagr_5yr"), errors="coerce")
    composite = pd.to_numeric(data.get("composite_score"), errors="coerce")
    debt_free = int((de.fillna(0) == 0).sum())

    cols = st.columns(6)
    cols[0].metric("Average ROE", _fmt(roe.mean(), "%"))
    cols[1].metric("Median P/E", _fmt(pe.median()))
    cols[2].metric("Median D/E", _fmt(de.median()))
    cols[3].metric("Total Companies", f"{len(data):,}")
    cols[4].metric("Median Revenue CAGR 5yr", _fmt(cagr.median(), "%"))
    cols[5].metric("Debt-Free Companies", f"{debt_free:,}")

    st.caption(f"Dashboard metrics for FY {year}")

    left, right = st.columns(2)
    with left:
        st.markdown("### Sector breakdown")
        sectors = data["sector"].fillna("Unknown").replace("", "Unknown").value_counts().reset_index()
        sectors.columns = ["sector", "company_count"]
        fig = px.pie(
            sectors,
            names="sector",
            values="company_count",
            hole=0.55,
            title="Companies by Sector",
        )
        fig.update_layout(margin=dict(t=40, l=10, r=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("### Top 5 companies by composite quality score")
        top = data.assign(composite_score=composite).dropna(subset=["composite_score"]).sort_values(
            "composite_score", ascending=False
        ).head(5)
        st.dataframe(
            top[["company_name", "ticker", "sector", "composite_score"]].rename(
                columns={"composite_score": "Composite Score"}
            ),
            use_container_width=True,
            hide_index=True,
        )
