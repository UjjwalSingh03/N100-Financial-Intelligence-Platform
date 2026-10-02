"""Main Streamlit entry point for the Nifty 100 Analytics dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.dashboard.utils.db import get_companies  # noqa: E402

PAGES = {
    "01 · Home": "src.dashboard.pages.01_home",
    "02 · Profile": "src.dashboard.pages.02_profile",
    "03 · Screener": "src.dashboard.pages.03_screener",
    "04 · Peers": "src.dashboard.pages.04_peers",
    "05 · Trends": "src.dashboard.pages.05_trends",
    "06 · Sectors": "src.dashboard.pages.06_sectors",
    "07 · Capital": "src.dashboard.pages.07_capital",
    "08 · Reports": "src.dashboard.pages.08_reports",
}


def _render_page(module_name: str) -> None:
    import importlib

    module = importlib.import_module(module_name)
    render = getattr(module, "render", None)
    if render is None:
        st.error(f"Dashboard page {module_name} does not expose render().")
        return
    render()


def main() -> None:
    st.sidebar.title("Nifty 100 Analytics")
    st.sidebar.caption("Sprint 4 · Dashboard & Valuation")

    selected_year = st.sidebar.selectbox(
        "Dashboard year",
        list(range(2024, 2018, -1)),
        index=0,
        key="dashboard_year",
        help="Home and company KPI metrics update for the selected financial year.",
    )

    selected = st.sidebar.radio("Navigate", list(PAGES))
    st.sidebar.divider()

    companies = get_companies()
    if companies.empty:
        st.sidebar.warning("Database not found or companies table is empty.")
    else:
        st.sidebar.caption(f"{len(companies)} companies available")

    _render_page(PAGES[selected])


if __name__ == "__main__":
    main()
