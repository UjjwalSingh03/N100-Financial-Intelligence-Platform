"""Portfolio-wide ten-KPI percentile table from Day 37 output."""
import csv
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["portfolio"])
STATS = Path(__file__).resolve().parents[3] / "output" / "portfolio_stats.csv"

@router.get("/portfolio/stats")
def portfolio_stats():
    if not STATS.is_file(): raise HTTPException(503, "Run Day 37 to generate portfolio_stats.csv")
    with STATS.open(newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))
    required = {"kpi", "P10", "P25", "P50", "P75", "P90"}
    if len(rows) != 10 or not rows or not required <= set(rows[0]):
        raise HTTPException(503, "Invalid Day 37 portfolio statistics output")
    return [{k: (r[k] if k == "kpi" else float(r[k]) if r.get(k) not in ("", None) else None) for k in r} for r in rows]
