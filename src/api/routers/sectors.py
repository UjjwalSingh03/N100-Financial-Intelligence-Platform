"""Sector overview and sector-company detail."""
import sqlite3
from statistics import median
from fastapi import APIRouter, Depends, HTTPException
from src.api.db import get_connection
from ._common import metrics

router = APIRouter(tags=["sectors"])

def med(rows, key):
    values = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
    return median(values) if values else None

@router.get("/sectors")
def sectors(db: sqlite3.Connection = Depends(get_connection)):
    grouped = {}
    for row in metrics(db):
        grouped.setdefault(row.get("broad_sector") or "Unknown", []).append(row)
    return [{"sector": name, "company_count": len(rows),
             "median_roe": med(rows, "roe_pct"), "median_pe": med(rows, "pe_ratio"),
             "median_de": med(rows, "debt_to_equity")} for name, rows in sorted(grouped.items())]

@router.get("/sectors/{sector}/companies")
def sector_companies(sector: str, db: sqlite3.Connection = Depends(get_connection)):
    rows = [r for r in metrics(db) if (r.get("broad_sector") or "Unknown").casefold() == sector.casefold()]
    if not rows: raise HTTPException(404, "Unknown sector")
    return rows
