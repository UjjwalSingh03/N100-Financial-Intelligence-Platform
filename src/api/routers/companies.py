"""Day 39: company directory, profiles, annual histories, ratios and PDF downloads."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from src.api.db import get_connection

router = APIRouter(prefix="/companies", tags=["companies"])
ROOT = Path(__file__).resolve().parents[3]
PERIOD = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def tables(db):
    return {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def columns(db, table):
    if table not in tables(db):
        return set()
    return {r[1] for r in db.execute(f'PRAGMA table_info("{table}")')}


def records(db, sql, params=()):
    return [dict(row) for row in db.execute(sql, params).fetchall()]


def company(db, ticker):
    if "companies" not in tables(db):
        raise HTTPException(503, "Companies table unavailable")
    row = db.execute(
        "SELECT * FROM companies WHERE UPPER(id)=UPPER(?) OR UPPER(ticker)=UPPER(?) OR UPPER(nse_code)=UPPER(?) LIMIT 1",
        (ticker, ticker, ticker)).fetchone()
    if row is None:
        raise HTTPException(404, "Ticker not found")
    return dict(row)


def sector_info(db, cid, base):
    result = {"broad_sector": base.get("sector"), "sub_sector": base.get("industry")}
    cols = columns(db, "sectors")
    if "company_id" in cols:
        sector_col = next((x for x in ("broad_sector", "sector") if x in cols), None)
        sub_col = next((x for x in ("sub_sector", "industry") if x in cols), None)
        row = db.execute("SELECT * FROM sectors WHERE company_id=? LIMIT 1", (cid,)).fetchone()
        if row:
            if sector_col: result["broad_sector"] = row[sector_col] or result["broad_sector"]
            if sub_col: result["sub_sector"] = row[sub_col] or result["sub_sector"]
    return result


def latest(db, table, cid):
    if not {"company_id", "year"} <= columns(db, table):
        return {}
    row = db.execute(f'SELECT * FROM "{table}" WHERE company_id=? ORDER BY year DESC LIMIT 1', (cid,)).fetchone()
    return dict(row) if row else {}


def market_cap_info(db, cid):
    if not {"company_id", "market_cap"} <= columns(db, "market_cap"):
        return (None, None)
    order = "ORDER BY year DESC" if "year" in columns(db, "market_cap") else ""
    row = db.execute(f"SELECT * FROM market_cap WHERE company_id=? {order} LIMIT 1", (cid,)).fetchone()
    if not row: return (None, None)
    amount = row["market_cap"]
    # Category boundaries in INR crore; explicitly documented rather than guessed from missing source labels.
    category = ("Large Cap" if amount >= 20000 else "Mid Cap" if amount >= 5000 else "Small Cap") if amount is not None else None
    return amount, category


def summary(db, base):
    cid = base["id"]
    ratios = latest(db, "financial_ratios", cid)
    sec = sector_info(db, cid, base)
    amount, category = market_cap_info(db, cid)
    return {"id": cid, "company_name": base["company_name"], **sec,
            "roe_pct": ratios.get("return_on_equity_pct"),
            "roce_pct": ratios.get("roce_percentage", base.get("roce_percentage")),
            "market_cap_category": category, "market_cap_cr": amount}


@router.get("")
def list_companies(sector: str | None = None, market_cap_category: str | None = None,
                   search: str | None = None, db: sqlite3.Connection = Depends(get_connection)):
    if "companies" not in tables(db):
        raise HTTPException(503, "Companies table unavailable")
    companies = records(db, "SELECT * FROM companies ORDER BY id COLLATE NOCASE")
    result = []
    for item in companies:
        row = summary(db, item)
        if sector and (row["broad_sector"] or "").casefold() != sector.casefold(): continue
        if market_cap_category and (row["market_cap_category"] or "").casefold() != market_cap_category.casefold(): continue
        if search and not any(search.casefold() in str(item.get(k) or "").casefold()
                              for k in ("id", "ticker", "nse_code", "company_name")): continue
        result.append(row)
    return result


@router.get("/{ticker}")
def get_company(ticker: str, db: sqlite3.Connection = Depends(get_connection)):
    base = company(db, ticker)
    cid = base["id"]
    return {**base, **summary(db, base),
            "latest_year_kpis": latest(db, "financial_ratios", cid),
            "latest_profit_and_loss": latest(db, "profitandloss", cid),
            "latest_balance_sheet": latest(db, "balancesheet", cid),
            "latest_cash_flow": latest(db, "cashflow", cid)}


def year_bounds(from_year, to_year):
    for value in (from_year, to_year):
        if value is not None and not PERIOD.fullmatch(value):
            raise HTTPException(422, "Year filters must use YYYY-MM")
    if from_year and to_year and from_year > to_year:
        raise HTTPException(422, "from_year must not exceed to_year")
    # Annual records use integer years. Match YYYY-MM against the calendar year
    # rather than pretending annual data has monthly precision.
    return (int(from_year[:4]) if from_year else None,
            int(to_year[:4]) if to_year else None)


def history(db, ticker, table, from_year=None, to_year=None):
    cid = company(db, ticker)["id"]
    if not {"company_id", "year"} <= columns(db, table):
        raise HTTPException(503, f"{table} unavailable")
    lower, upper = year_bounds(from_year, to_year)
    sql = f'SELECT * FROM "{table}" WHERE company_id=?'
    args = [cid]
    if lower is not None:
        sql += " AND year >= ?"; args.append(lower)
    if upper is not None:
        sql += " AND year <= ?"; args.append(upper)
    sql += " ORDER BY year ASC"
    return records(db, sql, args)


@router.get("/{ticker}/pl")
def profit_loss(ticker: str, from_year: str | None = None, to_year: str | None = None,
                db: sqlite3.Connection = Depends(get_connection)):
    return history(db, ticker, "profitandloss", from_year, to_year)


@router.get("/{ticker}/bs")
def balance_sheet(ticker: str, from_year: str | None = None, to_year: str | None = None,
                  db: sqlite3.Connection = Depends(get_connection)):
    return history(db, ticker, "balancesheet", from_year, to_year)


@router.get("/{ticker}/cashflow")
def cash_flow(ticker: str, from_year: str | None = None, to_year: str | None = None,
              db: sqlite3.Connection = Depends(get_connection)):
    return history(db, ticker, "cashflow", from_year, to_year)


@router.get("/{ticker}/ratios")
def ratios(ticker: str, year: int | None = Query(default=None, ge=1900, le=2200),
           db: sqlite3.Connection = Depends(get_connection)):
    rows = history(db, ticker, "financial_ratios")
    if year is None: return rows
    return next((row for row in rows if row["year"] == year), None)


@router.get("/{ticker}/tearsheet")
def tearsheet(ticker: str, db: sqlite3.Connection = Depends(get_connection)):
    base = company(db, ticker)
    cid = base["id"]
    if not re.fullmatch(r"[A-Za-z0-9._-]+", cid):
        raise HTTPException(400, "Invalid ticker filename")
    pdf = ROOT / "reports" / "tearsheets" / f"{cid}_tearsheet.pdf"
    if not pdf.is_file():
        raise HTTPException(404, "Pre-generated tearsheet not found")
    return FileResponse(pdf, media_type="application/pdf", filename=pdf.name)
