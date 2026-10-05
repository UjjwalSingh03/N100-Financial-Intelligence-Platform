"""Shared SQLite access helpers for the Streamlit dashboard."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"


@st.cache_data(ttl=600)
def _query(sql: str, params: tuple = (), db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    path = Path(db_path)
    if not path.exists():
        return pd.DataFrame()
    with sqlite3.connect(path) as conn:
        return pd.read_sql_query(sql, conn, params=params)


@st.cache_data(ttl=600)
def _table_columns(table_name: str, db_path: str = str(DEFAULT_DB_PATH)) -> list[str]:
    path = Path(db_path)
    if not path.exists():
        return []
    with sqlite3.connect(path) as conn:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row[1] for row in rows]


@st.cache_data(ttl=600)
def get_companies(db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return _query(
        "SELECT id, company_name, ticker, sector, industry, about_company, website, "
        "nse_profile, bse_profile FROM companies ORDER BY company_name",
        db_path=db_path,
    )


@st.cache_data(ttl=600)
def get_ratios(ticker: str, year: int | None = None, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    if year is None:
        return _query(
            "SELECT * FROM financial_ratios WHERE company_id=? ORDER BY year DESC",
            (ticker,), db_path,
        )
    return _query(
        "SELECT * FROM financial_ratios WHERE company_id=? AND year=? ORDER BY year DESC",
        (ticker, year), db_path,
    )


@st.cache_data(ttl=600)
def _company_statement(table: str, ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return _query(f"SELECT * FROM {table} WHERE company_id=? ORDER BY year DESC", (ticker,), db_path)


def get_pl(ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return _company_statement("profitandloss", ticker, db_path)


def get_bs(ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return _company_statement("balancesheet", ticker, db_path)


def get_cf(ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return _company_statement("cashflow", ticker, db_path)


@st.cache_data(ttl=600)
def get_sectors(db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return _query("SELECT * FROM sectors ORDER BY sector, company_id", db_path=db_path)


@st.cache_data(ttl=600)
def get_peers(group_name: str | None = None, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    if group_name:
        return _query(
            "SELECT * FROM peer_groups WHERE peer_group_name=? ORDER BY company_id",
            (group_name,), db_path,
        )
    return _query(
        "SELECT DISTINCT peer_group_name FROM peer_groups "
        "WHERE peer_group_name IS NOT NULL ORDER BY peer_group_name",
        db_path=db_path,
    )


@st.cache_data(ttl=600)
def get_valuation(ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    for table in ("market_cap", "financial_ratios", "analysis"):
        columns = _table_columns(table, db_path)
        if columns:
            select_cols = [c for c in ("year", "pe_ratio", "pb_ratio", "enterprise_value", "market_cap", "dividend_yield") if c in columns]
            if select_cols:
                return _query(
                    f"SELECT {', '.join(select_cols)} FROM {table} WHERE company_id=? ORDER BY year DESC",
                    (ticker,), db_path,
                )
    return pd.DataFrame()


@st.cache_data(ttl=600)
def get_home_snapshot(year: int, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    sql = """
    SELECT c.id AS company_id, c.company_name, c.ticker, c.sector,
           r.year, r.return_on_equity_pct AS roe,
           r.debt_to_equity AS de, r.revenue_cagr_5yr,
           r.composite_quality_score AS composite_score,
           m.pe_ratio, m.market_cap,
           r.free_cash_flow_cr AS fcf
    FROM companies c
    LEFT JOIN financial_ratios r ON r.company_id=c.id AND r.year=?
    LEFT JOIN market_cap m ON m.company_id=c.id AND m.year=?
    """
    return _query(sql, (year, year), db_path)


@st.cache_data(ttl=600)
def get_profile_ratios(ticker: str, year: int, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return _query(
        "SELECT * FROM financial_ratios WHERE company_id=? AND year=?",
        (ticker, year), db_path,
    )


@st.cache_data(ttl=600)
def get_profile_pl(ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return get_pl(ticker, db_path)


@st.cache_data(ttl=600)
def get_profile_history(ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    sql = """
    SELECT pl.year, pl.sales, pl.net_profit,
           r.return_on_equity_pct AS roe,
           CASE
               WHEN (COALESCE(bs.equity_capital,0) + COALESCE(bs.reserves,0) + COALESCE(bs.borrowings,0)) <> 0
               THEN (COALESCE(pl.operating_profit,0) /
                     (COALESCE(bs.equity_capital,0) + COALESCE(bs.reserves,0) + COALESCE(bs.borrowings,0))) * 100.0
               ELSE NULL
           END AS roce
    FROM profitandloss pl
    LEFT JOIN financial_ratios r ON r.company_id=pl.company_id AND r.year=pl.year
    LEFT JOIN balancesheet bs ON bs.company_id=pl.company_id AND bs.year=pl.year
    WHERE pl.company_id=?
    ORDER BY pl.year
    """
    return _query(sql, (ticker,), db_path)


@st.cache_data(ttl=600)
def get_profile_pros_cons(ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return _query("SELECT * FROM prosandcons WHERE company_id=? ORDER BY id", (ticker,), db_path)


@st.cache_data(ttl=600)
def get_screener_data(year: int, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    """Return one row per company for the selected screener year.

    P/E, P/B and dividend yield come from market_cap when those columns exist.
    The analysis table is intentionally not joined because it is a summary table
    and does not contain a year column in the dashboard database.
    """
    market_cap_cols = _table_columns("market_cap", db_path)
    pe_expr = "m.pe_ratio" if "pe_ratio" in market_cap_cols else "NULL"
    pb_expr = "m.pb_ratio" if "pb_ratio" in market_cap_cols else "NULL"
    dy_expr = "m.dividend_yield" if "dividend_yield" in market_cap_cols else "NULL"

    sql = f"""
    SELECT c.id AS company_id, c.company_name, c.ticker, c.sector,
           r.year, r.return_on_equity_pct AS roe,
           r.debt_to_equity AS de, r.free_cash_flow_cr AS fcf,
           r.revenue_cagr_5yr, r.pat_cagr_5yr,
           r.operating_profit_margin_pct AS opm,
           r.interest_coverage AS icr,
           r.composite_quality_score AS composite_score,
           {pe_expr} AS pe_ratio, {pb_expr} AS pb_ratio,
           {dy_expr} AS dividend_yield
    FROM companies c
    LEFT JOIN financial_ratios r ON r.company_id=c.id AND r.year=?
    LEFT JOIN market_cap m ON m.company_id=c.id AND m.year=?
    """
    return _query(sql, (year, year), db_path)


@st.cache_data(ttl=600)
def get_peer_groups(db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return get_peers(None, db_path)


@st.cache_data(ttl=600)
def get_peer_comparison(group_name: str, year: int, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    sql = """
    SELECT pp.company_id, c.company_name, c.ticker, c.sector,
           pp.metric, pp.value, pp.percentile_rank, pp.year
    FROM peer_percentiles pp
    LEFT JOIN companies c ON c.id=pp.company_id
    WHERE pp.peer_group_name=? AND pp.year=?
    ORDER BY c.company_name, pp.metric
    """
    return _query(sql, (group_name, year), db_path)


@st.cache_data(ttl=600)
def get_peer_radar(group_name: str, ticker: str, year: int, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    sql = """
    WITH selected AS (
        SELECT metric, value
        FROM peer_percentiles
        WHERE peer_group_name=? AND company_id=? AND year=?
    ),
    averages AS (
        SELECT metric, AVG(value) AS peer_average
        FROM peer_percentiles
        WHERE peer_group_name=? AND year=?
        GROUP BY metric
    )
    SELECT s.metric, s.value AS company, a.peer_average
    FROM selected s
    LEFT JOIN averages a ON a.metric=s.metric
    ORDER BY s.metric
    """
    return _query(sql, (group_name, ticker, year, group_name, year), db_path)


@st.cache_data(ttl=600)
def get_trend_data(ticker: str, metrics: Iterable[str], db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    requested = [m for m in metrics if m in {"roe", "roce", "revenue", "net_profit", "eps"}]
    if not requested:
        return pd.DataFrame()
    select = ["pl.year"]
    if "revenue" in requested:
        select.append("pl.sales AS revenue")
    if "net_profit" in requested:
        select.append("pl.net_profit")
    if "eps" in requested:
        select.append("pl.eps")
    if "roe" in requested:
        select.append("r.return_on_equity_pct AS roe")
    if "roce" in requested:
        select.append("r.roce_percentage AS roce" if "roce_percentage" in _table_columns("financial_ratios", db_path) else "NULL AS roce")
    sql = f"SELECT {', '.join(select)} FROM profitandloss pl LEFT JOIN financial_ratios r ON r.company_id=pl.company_id AND r.year=pl.year WHERE pl.company_id=? ORDER BY pl.year"
    return _query(sql, (ticker,), db_path)


@st.cache_data(ttl=600)
def get_sector_analysis(sector: str, year: int, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    sql = """
    SELECT c.id AS company_id, c.company_name, c.ticker, c.sector,
           r.return_on_equity_pct AS roe,
           pl.sales AS revenue,
           m.market_cap,
           s.industry
    FROM companies c
    LEFT JOIN sectors s ON s.company_id=c.id
    LEFT JOIN financial_ratios r ON r.company_id=c.id AND r.year=?
    LEFT JOIN profitandloss pl ON pl.company_id=c.id AND pl.year=?
    LEFT JOIN market_cap m ON m.company_id=c.id AND m.year=?
    WHERE c.sector=?
    ORDER BY c.company_name
    """
    return _query(sql, (year, year, year, sector), db_path)


@st.cache_data(ttl=600)
def get_sector_groups(db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return _query("SELECT DISTINCT sector FROM companies WHERE sector IS NOT NULL ORDER BY sector", db_path=db_path)


@st.cache_data(ttl=600)
def get_capital_allocation(year: int, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    sql = """
    SELECT c.id AS company_id, c.company_name, c.sector,
           cf.cash_from_operating_activity AS cfo,
           cf.cash_from_investing_activity AS cfi,
           cf.cash_from_financing_activity AS cff
    FROM companies c
    LEFT JOIN cashflow cf ON cf.company_id=c.id AND cf.year=?
    """
    return _query(sql, (year,), db_path)


@st.cache_data(ttl=600)
def get_annual_reports(ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return _query(
        "SELECT * FROM documents WHERE company_id=? ORDER BY document_date DESC, document_id DESC",
        (ticker,), db_path,
    )
