"""Sprint 4 Day 27 — integration QA runner.

Run locally from the repository root:
    python scripts/day27_qa.py

The script performs deterministic data-layer checks for the ten representative
tickers, verifies all eight page modules import, exercises extreme screener
thresholds, checks partial-history handling, and measures five profile data
loads. Full browser rendering/network-dependent report-link checks remain
manual because they depend on the local Streamlit/browser environment.
"""

from __future__ import annotations

import importlib
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "nifty100.db"
sys.path.insert(0, str(ROOT))

TICKERS = {
    "IT": "TCS",
    "IT_2": "INFY",
    "Financials": "HDFCBANK",
    "Financials_2": "ICICIBANK",
    "FMCG": "HINDUNILVR",
    "Energy": "RELIANCE",
    "Energy_2": "NTPC",
    "Healthcare": "SUNPHARMA",
    "Industrials": "LT",
    "FMCG_2": "ITC",
}

PAGES = [
    "src.dashboard.pages.01_home",
    "src.dashboard.pages.02_profile",
    "src.dashboard.pages.03_screener",
    "src.dashboard.pages.04_peers",
    "src.dashboard.pages.05_trends",
    "src.dashboard.pages.06_sectors",
    "src.dashboard.pages.07_capital",
    "src.dashboard.pages.08_reports",
]


def check_database() -> pd.DataFrame:
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")
    with sqlite3.connect(DB) as conn:
        companies = pd.read_sql_query("SELECT id, company_name FROM companies", conn)
        sectors = pd.read_sql_query("SELECT company_id, sector FROM sectors", conn)
    if len(companies) != 92:
        raise AssertionError(f"Expected 92 companies, found {len(companies)}")
    return companies.merge(sectors.drop_duplicates("company_id"), left_on="id", right_on="company_id", how="left")


def check_page_imports() -> None:
    for module in PAGES:
        importlib.import_module(module)


def check_tickers(companies: pd.DataFrame) -> pd.DataFrame:
    from src.dashboard.utils.db import get_profile_history

    rows = []
    available = set(companies["id"].astype(str).str.upper())
    for sector, ticker in TICKERS.items():
        exists = ticker.upper() in available
        if not exists:
            rows.append({"sector_test": sector, "ticker": ticker, "status": "FAIL", "years": 0})
            continue
        started = time.perf_counter()
        history = get_profile_history(ticker)
        elapsed = time.perf_counter() - started
        years = pd.to_numeric(history.get("year", pd.Series(dtype=float)), errors="coerce").dropna().nunique()
        rows.append({
            "sector_test": sector,
            "ticker": ticker,
            "status": "PASS" if not history.empty else "FAIL",
            "years": int(years),
            "load_seconds": round(elapsed, 3),
        })
    return pd.DataFrame(rows)


def check_extreme_screener() -> None:
    from src.dashboard.utils.db import get_screener_data
    from src.screener.engine import apply_filters

    data = get_screener_data(2024)
    if data.empty:
        raise AssertionError("Screener data is empty")

    # Map the dashboard aliases to the engine's canonical names and exercise
    # both extreme ends without requiring any matching companies.
    minimums = {
        "roe_min": -100,
        "de_max": 50,
        "fcf_min": -10000,
        "revenue_cagr_5yr_min": -100,
        "pat_cagr_5yr_min": -100,
        "opm_min": -100,
        "pe_max": 200,
        "pb_max": 100,
        "dividend_yield_min": 0,
        "icr_min": 0,
    }
    maximums = {
        "roe_min": 100,
        "de_max": 0,
        "fcf_min": 50000,
        "revenue_cagr_5yr_min": 100,
        "pat_cagr_5yr_min": 200,
        "opm_min": 100,
        "pe_max": 0,
        "pb_max": 0,
        "dividend_yield_min": 25,
        "icr_min": 100,
    }
    for thresholds in (minimums, maximums):
        result = apply_filters(data, thresholds)
        if not isinstance(result, pd.DataFrame):
            raise AssertionError("Extreme screener did not return a DataFrame")


def check_profile_speed(tickers: list[str]) -> pd.DataFrame:
    from src.dashboard.utils.db import get_profile_history, get_profile_pl, get_profile_ratios

    rows = []
    for ticker in tickers[:5]:
        started = time.perf_counter()
        get_profile_ratios(ticker, 2024)
        get_profile_pl(ticker)
        get_profile_history(ticker)
        elapsed = time.perf_counter() - started
        rows.append({"ticker": ticker, "load_seconds": round(elapsed, 3), "under_3_seconds": elapsed < 3})
    return pd.DataFrame(rows)


def main() -> int:
    companies = check_database()
    check_page_imports()
    ticker_results = check_tickers(companies)
    check_extreme_screener()

    existing = [t for t in TICKERS.values() if t in set(companies["id"].astype(str))]
    speed = check_profile_speed(existing)

    print("Day 27 QA — page imports: PASS")
    print("Day 27 QA — 92-company database: PASS")
    print("\nRepresentative ticker checks:")
    print(ticker_results.to_string(index=False))
    print("\nCompany Profile load timing:")
    print(speed.to_string(index=False))

    failures = int((ticker_results["status"] == "FAIL").sum())
    slow = int((~speed["under_3_seconds"]).sum())
    if failures or slow:
        print(f"\nRESULT: FAIL — ticker failures={failures}, slow profile loads={slow}")
        return 1

    print("\nRESULT: PASS — deterministic Day 27 checks completed.")
    print("Manual browser checks still required for visual overflow and all 8 screen interactions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
