"""Cached SQLite access helpers for the Streamlit dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"


def _db_path(db_path: str | Path | None = None) -> Path:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


@st.cache_data(ttl=600)
def _query(sql: str, params: tuple = (), db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    """Execute one read-only query and return a DataFrame."""
    import sqlite3

    path = _db_path(db_path)
    if not path.exists():
        return pd.DataFrame()

    with sqlite3.connect(path) as conn:
        return pd.read_sql_query(sql, conn, params=params)


@st.cache_data(ttl=600)
def _table_columns(table: str, db_path: str = str(DEFAULT_DB_PATH)) -> list[str]:
    import sqlite3

    path = _db_path(db_path)
    if not path.exists():
        return []
    with sqlite3.connect(path) as conn:
        rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    return [row[1] for row in rows]


@st.cache_data(ttl=600)
def get_companies(db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return _query(
        "SELECT * FROM companies ORDER BY company_name, id",
        db_path=db_path,
    )


@st.cache_data(ttl=600)
def get_ratios(
    ticker: str,
    year: Optional[int] = None,
    db_path: str = str(DEFAULT_DB_PATH),
) -> pd.DataFrame:
    columns = _table_columns("financial_ratios", db_path)
    if not columns:
        return pd.DataFrame()

    company = get_companies(db_path)
    if company.empty:
        return pd.DataFrame()

    id_col = "id" if "id" in company.columns else "company_id"
    ticker_col = next((c for c in ("ticker", "symbol") if c in company.columns), None)
    if not ticker_col:
        return pd.DataFrame()

    matches = company.loc[
        company[ticker_col].astype(str).str.upper() == str(ticker).upper()
    ]
    if matches.empty:
        return pd.DataFrame()

    company_id = matches.iloc[0][id_col]
    sql = "SELECT * FROM financial_ratios WHERE company_id = ?"
    params: tuple = (company_id,)
    if year is not None and "year" in columns:
        sql += " AND year = ?"
        params = (company_id, year)
    if "year" in columns:
        sql += " ORDER BY year DESC"
    return _query(sql, params, db_path)


def _company_statement(table: str, ticker: str, db_path: str) -> pd.DataFrame:
    columns = _table_columns(table, db_path)
    if not columns:
        return pd.DataFrame()
    company = get_companies(db_path)
    ticker_col = next((c for c in ("ticker", "symbol") if c in company.columns), None)
    id_col = "id" if "id" in company.columns else "company_id"
    if not ticker_col:
        return pd.DataFrame()
    matches = company.loc[
        company[ticker_col].astype(str).str.upper() == str(ticker).upper()
    ]
    if matches.empty:
        return pd.DataFrame()
    sql = f'SELECT * FROM "{table}" WHERE company_id = ?'
    if "year" in columns:
        sql += " ORDER BY year DESC"
    return _query(sql, (matches.iloc[0][id_col],), db_path)


@st.cache_data(ttl=600)
def get_pl(ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return _company_statement("profitandloss", ticker, db_path)


@st.cache_data(ttl=600)
def get_bs(ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return _company_statement("balancesheet", ticker, db_path)


@st.cache_data(ttl=600)
def get_cf(ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return _company_statement("cashflow", ticker, db_path)


@st.cache_data(ttl=600)
def get_sectors(db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    tables = _table_columns("sectors", db_path)
    if not tables:
        return pd.DataFrame()
    return _query("SELECT * FROM sectors ORDER BY 1", db_path=db_path)


@st.cache_data(ttl=600)
def get_peers(
    group_name: str,
    db_path: str = str(DEFAULT_DB_PATH),
) -> pd.DataFrame:
    columns = _table_columns("peer_percentiles", db_path)
    if not columns:
        return pd.DataFrame()
    return _query(
        "SELECT * FROM peer_percentiles WHERE peer_group_name = ? ORDER BY year DESC, metric, percentile_rank DESC",
        (group_name,),
        db_path,
    )


@st.cache_data(ttl=600)
def get_valuation(ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    """Return valuation-related fields when they exist in the database."""
    company = get_companies(db_path)
    if company.empty:
        return pd.DataFrame()

    ticker_col = next((c for c in ("ticker", "symbol") if c in company.columns), None)
    id_col = "id" if "id" in company.columns else "company_id"
    if not ticker_col:
        return pd.DataFrame()

    matches = company.loc[
        company[ticker_col].astype(str).str.upper() == str(ticker).upper()
    ]
    if matches.empty:
        return pd.DataFrame()

    company_id = matches.iloc[0][id_col]
    candidates = ["analysis", "financial_ratios", "market_cap"]
    for table in candidates:
        columns = _table_columns(table, db_path)
        if columns:
            return _query(
                f'SELECT * FROM "{table}" WHERE company_id = ? ORDER BY year DESC',
                (company_id,),
                db_path,
            )
    return pd.DataFrame()
