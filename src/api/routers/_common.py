"""Shared read-only query helpers for Day 40."""
import sqlite3
from fastapi import HTTPException
from src.api.routers.companies import columns, records, latest, sector_info, company

def required(db, table):
    if not columns(db, table):
        raise HTTPException(503, f"{table} unavailable")

def metrics(db):
    required(db, "companies")
    rows = records(db, "SELECT * FROM companies ORDER BY id")
    result = []
    for c in rows:
        cid = c["id"]
        r = latest(db, "financial_ratios", cid)
        p = latest(db, "profitandloss", cid)
        b = latest(db, "balancesheet", cid)
        mc = latest(db, "market_cap", cid)
        equity = (b.get("equity_capital") or 0) + (b.get("reserves") or 0) + (b.get("borrowings") or 0)
        roce = (100 * p["operating_profit"] / equity) if equity > 0 and p.get("operating_profit") is not None else None
        pe = (mc["market_cap"] / p["net_profit"]) if mc.get("market_cap") is not None and p.get("net_profit") is not None and p["net_profit"] > 0 else None
        result.append({**c, **sector_info(db, cid, c), **r, "company_id": cid,
                       "roe_pct": r.get("return_on_equity_pct"), "roce_pct": roce,
                       "pe_ratio": pe, "market_cap_cr": mc.get("market_cap"),
                       "net_profit": p.get("net_profit"), "sales": p.get("sales")})
    return result
