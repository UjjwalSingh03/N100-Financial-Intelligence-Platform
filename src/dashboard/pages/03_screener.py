"""Sprint 4 Day 24 — interactive screener."""
from __future__ import annotations
import streamlit as st
from src.dashboard.utils.db import get_screener_data
from src.screener.engine import apply_filters

PRESETS = {
    "Quality": {"roe_min": 15.0, "de_max": 1.0, "fcf_min": 0.0, "revenue_cagr_5yr_min": 10.0},
    "Value": {"pe_max": 30.0, "pb_max": 5.0, "de_max": 3.0, "dividend_yield_min": 0.0},
    "Growth": {"pat_cagr_5yr_min": 20.0, "revenue_cagr_5yr_min": 15.0, "de_max": 2.0},
    "Dividend": {"dividend_yield_min": 2.0, "fcf_min": 0.0},
    "Debt-Free": {"de_max": 0.01, "roe_min": 10.0},
    "Turnaround": {"revenue_cagr_5yr_min": 10.0, "fcf_min": 0.0},
}
DEFAULTS = {"roe_min":0.0,"de_max":20.0,"fcf_min":-10000.0,"revenue_cagr_5yr_min":-100.0,"pat_cagr_5yr_min":-100.0,"opm_min":-100.0,"pe_max":200.0,"pb_max":100.0,"dividend_yield_min":0.0,"icr_min":0.0}

def _apply_preset(name):
    for metric,value in PRESETS[name].items():
        st.session_state[f"filter_{metric}"] = value
    st.session_state["active_preset"] = name

def render():
    st.title("Financial Screener")
    year = int(st.session_state.get("dashboard_year", 2024))
    data = get_screener_data(year)
    if data.empty:
        st.info("Database not available. Add db/nifty100.db and reload.")
        return

    st.sidebar.markdown("### Screener Presets")
    buttons = st.sidebar.columns(2)
    for i,name in enumerate(PRESETS):
        if buttons[i % 2].button(name, key=f"preset_{name}"):
            _apply_preset(name)
            st.rerun()

    st.sidebar.markdown("### Filters")
    ranges = {
        "roe_min":("ROE min",-100.0,100.0,0.5),
        "de_max":("D/E max",0.0,50.0,0.1),
        "fcf_min":("FCF min",-10000.0,50000.0,100.0),
        "revenue_cagr_5yr_min":("Revenue CAGR min",-100.0,100.0,0.5),
        "pat_cagr_5yr_min":("PAT CAGR min",-100.0,200.0,0.5),
        "opm_min":("OPM min",-100.0,100.0,0.5),
        "pe_max":("P/E max",0.0,200.0,1.0),
        "pb_max":("P/B max",0.0,100.0,0.5),
        "dividend_yield_min":("Dividend Yield min",0.0,25.0,0.1),
        "icr_min":("ICR min",0.0,100.0,0.1),
    }
    for key,(label,lo,hi,step) in ranges.items():
        sk=f"filter_{key}"
        if sk not in st.session_state: st.session_state[sk]=DEFAULTS[key]
        st.sidebar.slider(label,lo,hi,st.session_state[sk],step=step,key=sk)

    thresholds={k:st.session_state[f"filter_{k}"] for k in ranges}
    try:
        result=apply_filters(data,thresholds)
    except (KeyError,ValueError) as exc:
        st.warning(f"Some filter data is unavailable: {exc}")
        result=data.copy()

    visible=[c for c in ["company_id","company_name","sector","composite_score","roe","de","fcf","revenue_cagr_5yr","pat_cagr_5yr","opm","pe_ratio","pb_ratio","dividend_yield","icr"] if c in result.columns]
    visible_df=result[visible].copy()
    st.markdown(f"### {len(visible_df)} companies match your filters")
    st.dataframe(visible_df,use_container_width=True,hide_index=True)
    st.download_button("Download CSV",visible_df.to_csv(index=False).encode("utf-8"),file_name=f"screener_{year}.csv",mime="text/csv")
