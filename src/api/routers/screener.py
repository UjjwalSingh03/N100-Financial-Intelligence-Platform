"""Filter latest company KPIs and rank by composite quality."""
import math
import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Request
from src.api.db import get_connection
from ._common import metrics

router = APIRouter(tags=["screener"])
FILTERS = {"min_roe": ("roe_pct", True), "max_de": ("debt_to_equity", False),
           "min_fcf": ("free_cash_flow_cr", True),
           "min_rev_cagr_5yr": ("revenue_cagr_5yr", True),
           "min_pat_cagr_5yr": ("pat_cagr_5yr", True), "max_pe": ("pe_ratio", False)}

@router.get("/screener")
def screen(request: Request, min_roe: float | None = None, max_de: float | None = None,
           min_fcf: float | None = None, sector: str | None = None,
           min_rev_cagr_5yr: float | None = None, min_pat_cagr_5yr: float | None = None,
           max_pe: float | None = None, db: sqlite3.Connection = Depends(get_connection)):
    params = locals()
    for key in request.query_params:
        if key not in (*FILTERS, "sector"):
            raise HTTPException(400, f"Unknown filter: {key}")
    for key in FILTERS:
        raw = request.query_params.get(key)
        if raw is not None:
            try: val = float(raw)
            except ValueError: raise HTTPException(400, f"Invalid {key}")
            if not math.isfinite(val) or (key in ("max_de", "max_pe") and val < 0):
                raise HTTPException(400, f"Invalid {key}")
    rows = metrics(db)
    out = []
    for row in rows:
        if sector and (row.get("broad_sector") or "").casefold() != sector.casefold(): continue
        valid = True
        for key, (field, minimum) in FILTERS.items():
            bound = params[key]
            if bound is None: continue
            value = row.get(field)
            # Missing metric cannot pass a selected threshold.
            if value is None or not isinstance(value, (float, int)) or not math.isfinite(value):
                valid = False; break
            if (minimum and value < bound) or (not minimum and value > bound):
                valid = False; break
        if valid: out.append(row)
    return sorted(out, key=lambda r: (-(r.get("composite_quality_score") or -1), r["company_id"]))
