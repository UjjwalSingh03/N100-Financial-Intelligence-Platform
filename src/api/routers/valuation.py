"""Historical market-cap valuation multiples."""
import sqlite3
from fastapi import APIRouter, Depends
from src.api.db import get_connection
from .companies import company, columns, records

router = APIRouter(tags=["valuation"])

@router.get("/market-cap/{ticker}")
def market_cap(ticker: str, db: sqlite3.Connection = Depends(get_connection)):
    cid = company(db, ticker)["id"]
    cols = columns(db, "market_cap")
    if not {"company_id", "year"} <= cols: return []
    mc = records(db, "SELECT * FROM market_cap WHERE company_id=? AND year BETWEEN 2019 AND 2024 ORDER BY year", (cid,))
    pnl = {r["year"]: r for r in records(db, "SELECT * FROM profitandloss WHERE company_id=? AND year BETWEEN 2019 AND 2024", (cid,))} if columns(db, "profitandloss") else {}
    out = []
    for row in mc:
        p = pnl.get(row["year"], {})
        cap, profit = row.get("market_cap"), p.get("net_profit")
        pe = row.get("pe_ratio") if "pe_ratio" in cols else (cap / profit if cap is not None and profit is not None and profit > 0 else None)
        out.append({"year": row["year"], "market_cap_cr": cap, "pe_ratio": pe,
                    "pb_ratio": row.get("pb_ratio"), "ev_ebitda": row.get("ev_ebitda"),
                    "dividend_yield_pct": row.get("dividend_yield_pct")})
    return out
