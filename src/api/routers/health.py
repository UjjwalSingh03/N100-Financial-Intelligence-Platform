"""API health and database row-count endpoint."""
import sqlite3
import time
from fastapi import APIRouter, Depends, HTTPException
from src.api.db import get_connection

router = APIRouter(tags=["health"])
CORE_TABLES = ("companies", "profitandloss", "balancesheet", "cashflow",
               "analysis", "documents", "prosandcons", "sectors",
               "stock_prices", "financial_ratios")


@router.get("/health")
def health(db: sqlite3.Connection = Depends(get_connection)):
    from src.api.main import STARTED_AT, VERSION
    try:
        available = {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        missing = [table for table in CORE_TABLES if table not in available]
        if missing:
            raise HTTPException(status_code=503, detail={"missing_tables": missing})
        counts = {table: db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                  for table in CORE_TABLES}
    except sqlite3.DatabaseError as exc:
        raise HTTPException(status_code=503, detail="Database health check failed") from exc
    return {"status": "ok", "db_row_counts": counts,
            "uptime_seconds": round(time.monotonic() - STARTED_AT, 3),
            "version": VERSION}
