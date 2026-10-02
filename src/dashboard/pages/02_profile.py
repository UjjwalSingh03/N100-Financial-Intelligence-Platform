"""Sprint 4 Day 23 — Company Profile dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import (
    get_companies,
    get_profile_pl,
    get_profile_pros_cons,
    get_profile_ratios,
)


def _num(df, column):
    if column not in df.columns or df.empty:
        return None
    s = pd.to_numeric(df[column], errors="coerce").dropna()
    return None if s.empty else float(s.iloc[0])


def _company_text(row, candidates, fallback="Not available in current database"):
    for col in candidates:
        if col in row.index and pd.notna(row[col]) and str(row[col]).strip():
            return str(row[col])
    return fallback


def _metric(value, suffix=""):
    return "N/A" if value is None else f"{value:.2f}{suffix}"


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

    # Search/autocomplete: filtering the selectbox options gives a native
    # searchable dropdown while keeping the complete company universe.
    search = st.text_input("Search company or ticker", placeholder="Type company name or NSE ticker…")
    options = companies.copy()
    if search.strip():
        q = search.strip().lower()
        mask = (
            options["company_name"].astype(str).str.lower().str.contains(q, na=False)
            | options[ticker_col].astype(str).str.lower().str.contains(q, na=False)
        )
        options = options.loc[mask]

    if options.empty:
        st.warning("Ticker not found — please try another")
        return

    options = options.sort_values("company_name")
    labels = [
        f"{row.company_name} ({getattr(row, ticker_col)})"
        for row in options.itertuples(index=False)
    ]
    selected_label = st.selectbox("Company", labels)
    selected_idx = labels.index(selected_label)
    row = options.iloc[selected_idx]
    ticker = str(row[ticker_col])

    year = int(st.session_state.get("dashboard_year", 2024))
    ratios = get_profile_ratios(ticker, year)
    pl = get_profile_pl(ticker)

    st.markdown("### Company")
    st.markdown(f"## {row.get('company_name', ticker)}")
    c1, c2, c3 = st.columns(3)
    c1.write(f"**Sector:** {_company_text(row, ['sector'])}")
    c2.write(f"**Sub-sector:** {_company_text(row, ['sub_sector', 'subsector', 'industry'])}")
    c3.write(f"**NSE ticker:** {ticker}")
    about = _company_text(row, ["about", "description", "about_description", "business_description"])
    st.info(f"**About:** {about}")

    r = ratios.iloc[0] if not ratios.empty else pd.Series(dtype=object)
    k = st.columns(6)
    k[0].metric("ROE", _metric(_num(ratios, "return_on_equity_pct"), "%"))
    k[1].metric("ROCE", _metric(_num(ratios, "return_on_capital_employed_pct"), "%"))
    k[2].metric("Net Profit Margin", _metric(_num(ratios, "net_profit_margin_pct"), "%"))
    k[3].metric("D/E", _metric(_num(ratios, "debt_to_equity")))
    k[4].metric("Revenue CAGR 5yr", _metric(_num(ratios, "revenue_cagr_5yr"), "%"))
    k[5].metric("FCF", _metric(_num(ratios, "free_cash_flow_cr"), " Cr"))

    st.caption(f"Financial KPIs for FY {year}")

    if pl.empty:
        st.info("No P&L history available for this company.")
    else:
        hist = pl.copy()
        hist["year"] = pd.to_numeric(hist["year"], errors="coerce")
        hist = hist.dropna(subset=["year"]).sort_values("year").tail(10)

        st.markdown("### Revenue & Net Profit — 10 years")
        fig = go.Figure()
        if "sales" in hist.columns:
            fig.add_trace(go.Bar(x=hist["year"], y=pd.to_numeric(hist["sales"], errors="coerce"),
                                 name="Revenue"))
        if "net_profit" in hist.columns:
            fig.add_trace(go.Bar(x=hist["year"], y=pd.to_numeric(hist["net_profit"], errors="coerce"),
                                 name="Net Profit"))
        fig.update_layout(barmode="group", xaxis_title="Year", yaxis_title="₹ Cr",
                          legend_title="")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### ROE & ROCE — 10 years")
        ratio_hist = get_profile_ratios(ticker, None)
        ratio_hist["year"] = pd.to_numeric(ratio_hist["year"], errors="coerce")
        ratio_hist = ratio_hist.dropna(subset=["year"]).sort_values("year").tail(10)
        fig2 = go.Figure()
        if "return_on_equity_pct" in ratio_hist.columns:
            fig2.add_trace(go.Scatter(
                x=ratio_hist["year"], y=pd.to_numeric(ratio_hist["return_on_equity_pct"], errors="coerce"),
                mode="lines+markers", name="ROE"
            ))
        roce_col = "return_on_capital_employed_pct"
        if roce_col in ratio_hist.columns:
            fig2.add_trace(go.Scatter(
                x=ratio_hist["year"], y=pd.to_numeric(ratio_hist[roce_col], errors="coerce"),
                mode="lines+markers", name="ROCE", yaxis="y2"
            ))
        fig2.update_layout(
            xaxis_title="Year", yaxis_title="ROE (%)",
            yaxis2=dict(title="ROCE (%)", overlaying="y", side="right"),
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### Pros & Cons")
    pc = get_profile_pros_cons(ticker)
    if pc.empty:
        st.info("No pros/cons data available.")
    else:
        type_col = next((c for c in ("item_type", "type", "category") if c in pc.columns), None)
        text_col = next((c for c in ("description", "item", "text", "value") if c in pc.columns), None)
        if text_col:
            for _, item in pc.iterrows():
                kind = str(item[type_col]).lower() if type_col else "pro"
                icon = "✅" if "pro" in kind or "positive" in kind else "❌"
                st.markdown(f"{icon} **{kind.title()}:** {item[text_col]}")
