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
    return _query("SELECT * FROM companies ORDER BY company_name, id", db_path=db_path)


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
    matches = company.loc[company[ticker_col].astype(str).str.upper() == str(ticker).upper()]
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


@st.cache_data(ttl=600)
def _company_statement(table: str, ticker: str, db_path: str) -> pd.DataFrame:
    columns = _table_columns(table, db_path)
    if not columns:
        return pd.DataFrame()
    company = get_companies(db_path)
    ticker_col = next((c for c in ("ticker", "symbol") if c in company.columns), None)
    id_col = "id" if "id" in company.columns else "company_id"
    if not ticker_col:
        return pd.DataFrame()
    matches = company.loc[company[ticker_col].astype(str).str.upper() == str(ticker).upper()]
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
    if not _table_columns("sectors", db_path):
        return pd.DataFrame()
    return _query("SELECT * FROM sectors ORDER BY 1", db_path=db_path)


@st.cache_data(ttl=600)
def get_peers(group_name: str | None = None, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    if not _table_columns("peer_percentiles", db_path):
        return pd.DataFrame()
    if group_name:
        return _query(
            "SELECT * FROM peer_percentiles WHERE peer_group_name = ? "
            "ORDER BY year DESC, metric, percentile_rank DESC",
            (group_name,),
            db_path,
        )
    return _query(
        "SELECT DISTINCT peer_group_name FROM peer_percentiles "
        "WHERE peer_group_name IS NOT NULL ORDER BY peer_group_name",
        db_path=db_path,
    )


@st.cache_data(ttl=600)
def get_screener_data(year: int, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    """Return one row per company for the selected screener year."""
    analysis_cols = _table_columns("analysis", db_path)
    pe_expr = 'a.pe_ratio' if "pe_ratio" in analysis_cols else 'NULL'
    pb_expr = 'a.pb_ratio' if "pb_ratio" in analysis_cols else 'NULL'
    dy_expr = 'a.dividend_yield_pct' if "dividend_yield_pct" in analysis_cols else (
        'a.dividend_yield' if "dividend_yield" in analysis_cols else 'NULL'
    )
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
    LEFT JOIN analysis a ON a.company_id=c.id AND a.year=?
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
    JOIN companies c ON c.id=pp.company_id
    WHERE pp.peer_group_name=? AND pp.year=?
    ORDER BY c.company_name, pp.metric
    """
    return _query(sql, (group_name, year), db_path)


@st.cache_data(ttl=600)
def get_peer_radar(group_name: str, ticker: str, year: int, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    data = get_peer_comparison(group_name, year, db_path)
    if data.empty:
        return data
    benchmark = data[data["ticker"].astype(str).str.upper() == str(ticker).upper()]
    avg = data.groupby("metric", as_index=False)["value"].mean()
    metrics = ["ROE", "ROCE", "Net Profit Margin", "D/E", "FCF", "PAT CAGR 5yr", "Revenue CAGR 5yr", "EPS CAGR 5yr"]
    rows = []
    for metric in metrics:
        b = benchmark.loc[benchmark["metric"].astype(str).str.lower() == metric.lower(), "value"]
        a = avg.loc[avg["metric"].astype(str).str.lower() == metric.lower(), "value"]
        rows.append({"metric": metric, "company": b.iloc[0] if not b.empty else None, "peer_average": a.iloc[0] if not a.empty else None})
    return pd.DataFrame(rows)


@st.cache_data(ttl=600)
def get_valuation(ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    company = get_companies(db_path)
    if company.empty:
        return pd.DataFrame()
    ticker_col = next((c for c in ("ticker", "symbol") if c in company.columns), None)
    id_col = "id" if "id" in company.columns else "company_id"
    if not ticker_col:
        return pd.DataFrame()
    matches = company.loc[company[ticker_col].astype(str).str.upper() == str(ticker).upper()]
    if matches.empty:
        return pd.DataFrame()
    company_id = matches.iloc[0][id_col]
    for table in ("analysis", "financial_ratios", "market_cap"):
        columns = _table_columns(table, db_path)
        if columns:
            year_col = "year" if "year" in columns else "metric_year"
            return _query(
                f'SELECT * FROM "{table}" WHERE company_id = ? ORDER BY "{year_col}" DESC',
                (company_id,),
                db_path,
            )
    return pd.DataFrame()


@st.cache_data(ttl=600)
def get_home_snapshot(year: int, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    """One row per company for the selected dashboard year."""
    sql = """
    SELECT c.id AS company_id, c.company_name, c.ticker, c.sector, c.industry,
           r.year, r.return_on_equity_pct, r.debt_to_equity,
           r.revenue_cagr_5yr, r.composite_quality_score,
           r.free_cash_flow_cr, r.operating_profit_margin_pct,
           m.market_cap, p.net_profit, p.operating_profit,
           b.equity_capital, b.reserves, b.borrowings
    FROM companies c
    LEFT JOIN financial_ratios r ON r.company_id = c.id AND r.year = ?
    LEFT JOIN market_cap m ON m.company_id = c.id AND m.year = ?
    LEFT JOIN profitandloss p ON p.company_id = c.id AND p.year = ?
    LEFT JOIN balancesheet b ON b.company_id = c.id AND b.year = ?
    """
    result = _query(sql, (year, year, year, year), db_path)
    if result.empty:
        return result
    for col in ("market_cap", "net_profit", "operating_profit", "equity_capital", "reserves", "borrowings"):
        result[col] = pd.to_numeric(result[col], errors="coerce")
    result["pe_ratio"] = result["market_cap"].div(result["net_profit"].where(result["net_profit"] > 0))
    capital = result["equity_capital"].fillna(0) + result["reserves"].fillna(0) + result["borrowings"].fillna(0)
    result["roce_pct"] = result["operating_profit"].div(capital.where(capital > 0)).mul(100)
    return result


@st.cache_data(ttl=600)
def get_profile_ratios(ticker: str, year: int, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return get_ratios(ticker, year, db_path)


@st.cache_data(ttl=600)
def get_profile_pl(ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    return get_pl(ticker, db_path)


@st.cache_data(ttl=600)
def get_profile_history(ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    company = get_companies(db_path)
    if company.empty:
        return pd.DataFrame()
    ticker_col = next((c for c in ("ticker", "symbol") if c in company.columns), None)
    id_col = "id" if "id" in company.columns else "company_id"
    if not ticker_col:
        return pd.DataFrame()
    matches = company.loc[company[ticker_col].astype(str).str.upper() == str(ticker).upper()]
    if matches.empty:
        return pd.DataFrame()
    cid = matches.iloc[0][id_col]
    sql = """
    SELECT p.year, p.sales, p.net_profit, p.operating_profit,
           r.return_on_equity_pct, r.revenue_cagr_5yr, r.free_cash_flow_cr,
           b.equity_capital, b.reserves, b.borrowings
    FROM profitandloss p
    LEFT JOIN financial_ratios r ON r.company_id=p.company_id AND r.year=p.year
    LEFT JOIN balancesheet b ON b.company_id=p.company_id AND b.year=p.year
    WHERE p.company_id=?
    ORDER BY p.year
    """
    result = _query(sql, (cid,), db_path)
    if result.empty:
        return result
    capital = (
        pd.to_numeric(result["equity_capital"], errors="coerce").fillna(0)
        + pd.to_numeric(result["reserves"], errors="coerce").fillna(0)
        + pd.to_numeric(result["borrowings"], errors="coerce").fillna(0)
    )
    result["roce_pct"] = (
        pd.to_numeric(result["operating_profit"], errors="coerce")
        .div(capital.where(capital > 0))
        .mul(100)
    )
    return result


@st.cache_data(ttl=600)
def get_profile_pros_cons(ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    columns = _table_columns("prosandcons", db_path)
    if not columns:
        return pd.DataFrame()
    company = get_companies(db_path)
    ticker_col = next((c for c in ("ticker", "symbol") if c in company.columns), None)
    id_col = "id" if "id" in company.columns else "company_id"
    if not ticker_col:
        return pd.DataFrame()
    matches = company.loc[company[ticker_col].astype(str).str.upper() == str(ticker).upper()]
    if matches.empty:
        return pd.DataFrame()
    return _query(
        'SELECT * FROM "prosandcons" WHERE company_id = ? ORDER BY id',
        (matches.iloc[0][id_col],),
        db_path,
    )


@st.cache_data(ttl=600)
def get_trend_data(
    ticker: str,
    metrics: tuple[str, ...] = ("ROE",),
    db_path: str = str(DEFAULT_DB_PATH),
) -> pd.DataFrame:
    """Return 10-year company trend data for up to three selected metrics."""
    company = get_companies(db_path)
    if company.empty:
        return pd.DataFrame()
    ticker_col = next((c for c in ("ticker", "symbol") if c in company.columns), None)
    id_col = "id" if "id" in company.columns else "company_id"
    if not ticker_col:
        return pd.DataFrame()
    matches = company.loc[company[ticker_col].astype(str).str.upper() == str(ticker).upper()]
    if matches.empty:
        return pd.DataFrame()
    cid = matches.iloc[0][id_col]
    metric_map = {
        "ROE": "r.return_on_equity_pct",
        "ROCE": "(p.operating_profit / NULLIF(COALESCE(b.equity_capital,0)+COALESCE(b.reserves,0)+COALESCE(b.borrowings,0),0))*100",
        "Net Profit Margin": "r.net_profit_margin_pct",
        "Operating Profit Margin": "r.operating_profit_margin_pct",
        "D/E": "r.debt_to_equity",
        "FCF": "r.free_cash_flow_cr",
        "Revenue CAGR 5yr": "r.revenue_cagr_5yr",
        "PAT CAGR 5yr": "r.pat_cagr_5yr",
        "EPS CAGR 5yr": "r.eps_cagr_5yr",
        "Composite Score": "r.composite_quality_score",
    }
    selected = [m for m in metrics if m in metric_map][:3]
    if not selected:
        return pd.DataFrame()
    expressions = ", ".join(f"{metric_map[m]} AS \"{m}\"" for m in selected)
    sql = f"""
        SELECT p.year, p.sales AS Revenue, p.net_profit AS \"Net Profit\",
               {expressions}
        FROM profitandloss p
        LEFT JOIN financial_ratios r ON r.company_id=p.company_id AND r.year=p.year
        LEFT JOIN balancesheet b ON b.company_id=p.company_id AND b.year=p.year
        WHERE p.company_id=?
        ORDER BY p.year
    """
    result = _query(sql, (cid,), db_path)
    return result.tail(10).reset_index(drop=True) if not result.empty else result


@st.cache_data(ttl=600)
def get_sector_analysis(
    sector: str,
    year: int,
    db_path: str = str(DEFAULT_DB_PATH),
) -> pd.DataFrame:
    """Return company-level revenue, ROE, market cap and sub-sector for a sector."""
    sector_expr = "COALESCE(c.sector, s.sector)"
    industry_expr = "COALESCE(c.industry, s.industry)"
    sql = f"""
        SELECT c.id AS company_id, c.company_name, c.ticker,
               {sector_expr} AS sector, {industry_expr} AS sub_sector,
               p.sales AS revenue, r.return_on_equity_pct AS roe,
               m.market_cap
        FROM companies c
        LEFT JOIN sectors s ON s.company_id=c.id
        LEFT JOIN profitandloss p ON p.company_id=c.id AND p.year=?
        LEFT JOIN financial_ratios r ON r.company_id=c.id AND r.year=?
        LEFT JOIN market_cap m ON m.company_id=c.id AND m.year=?
        WHERE {sector_expr} = ?
        ORDER BY c.company_name
    """
    return _query(sql, (year, year, year, sector), db_path)


@st.cache_data(ttl=600)
def get_sector_groups(db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    """Return distinct sector names from the company universe."""
    if not _table_columns("companies", db_path):
        return pd.DataFrame()
    return _query(
        "SELECT DISTINCT sector FROM companies WHERE sector IS NOT NULL AND TRIM(sector) <> '' ORDER BY sector",
        db_path=db_path,
    )


@st.cache_data(ttl=600)
def get_capital_allocation(year: int, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    """Classify all companies for a selected year into the eight Day 11 patterns."""
    sql = """
        SELECT c.id AS company_id, c.company_name, c.ticker, cf.year,
               cf.cash_from_operating_activity AS cfo,
               cf.cash_from_investing_activity AS cfi,
               cf.cash_from_financing_activity AS cff,
               p.net_profit AS pat
        FROM companies c
        LEFT JOIN cashflow cf ON cf.company_id=c.id
        LEFT JOIN profitandloss p ON p.company_id=c.id AND p.year=cf.year
        ORDER BY c.id, cf.year
    """
    data = _query(sql, db_path=db_path)
    if data.empty:
        return data

    for col in ("cfo", "cfi", "cff", "pat"):
        data[col] = pd.to_numeric(data[col], errors="coerce")

    def sign(v):
        if pd.isna(v) or float(v) == 0:
            return "0"
        return "+" if float(v) > 0 else "-"

    data["cfo_pat"] = data["cfo"].div(data["pat"].where(data["pat"] != 0))
    data["cfo_quality"] = (
        data.groupby("company_id")["cfo_pat"]
        .transform(lambda s: s.rolling(5, min_periods=1).mean())
    )

    def classify(row):
        signs = (sign(row["cfo"]), sign(row["cfi"]), sign(row["cff"]))
        labels = {
            ("+","-","+"): "Mixed",
            ("+","+","+"): "Cash Accumulator",
            ("+","+","-"): "Liquidating Assets",
            ("-","+","+"): "Distress Signal",
            ("-","-","+"): "Growth Funded by Debt",
            ("-","-","-"): "Pre-Revenue",
        }
        if signs == ("+","-","-"):
            return "Shareholder Returns" if (row["cfo_quality"] or 0) > 1.0 else "Reinvestor"
        return labels.get(signs, "Mixed")

    data["pattern"] = data.apply(classify, axis=1)
    return data.loc[data["year"] == year, ["company_id","company_name","ticker","cfo","cfi","cff","pattern"]].reset_index(drop=True)


@st.cache_data(ttl=600)
def get_annual_reports(ticker: str, db_path: str = str(DEFAULT_DB_PATH)) -> pd.DataFrame:
    """Return annual-report document rows for a company."""
    columns = _table_columns("documents", db_path)
    if not columns:
        return pd.DataFrame()
    company = get_companies(db_path)
    ticker_col = next((c for c in ("ticker", "symbol") if c in company.columns), None)
    id_col = "id" if "id" in company.columns else "company_id"
    if not ticker_col:
        return pd.DataFrame()
    matches = company.loc[company[ticker_col].astype(str).str.upper() == str(ticker).upper()]
    if matches.empty:
        return pd.DataFrame()
    return _query(
        """
        SELECT id, document_type, document_url, document_date
        FROM documents
        WHERE company_id=?
          AND (LOWER(COALESCE(document_type,'')) LIKE '%annual%'
               OR LOWER(COALESCE(document_type,'')) LIKE '%report%')
        ORDER BY document_date DESC, id DESC
        """,
        (matches.iloc[0][id_col],),
        db_path,
    )
