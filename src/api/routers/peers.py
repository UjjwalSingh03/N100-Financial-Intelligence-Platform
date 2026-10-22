"""Peer group rankings and eight-axis radar comparison."""
import sqlite3
from statistics import mean
from fastapi import APIRouter, Depends, HTTPException
from src.api.db import get_connection
from ._common import metrics
from .companies import company, columns, records

router = APIRouter(tags=["peers"])
AXES = ("roe", "roce", "net_profit_margin", "debt_to_equity",
        "free_cash_flow", "pat_cagr_5yr", "revenue_cagr_5yr", "composite_score")
LOOKUP = {"roe": "roe_pct", "roce": "roce_pct", "net_profit_margin": "net_profit_margin_pct",
          "debt_to_equity": "debt_to_equity", "free_cash_flow": "free_cash_flow_cr",
          "pat_cagr_5yr": "pat_cagr_5yr", "revenue_cagr_5yr": "revenue_cagr_5yr",
          "composite_score": "composite_quality_score"}

def membership(db):
    if not {"company_id", "peer_group_name"} <= columns(db, "peer_groups"):
        raise HTTPException(503, "peer_groups unavailable")
    groups = {}
    for r in records(db, "SELECT * FROM peer_groups"):
        if r["peer_group_name"]:
            groups.setdefault(r["peer_group_name"], set()).add(r["company_id"])
            if r.get("peer_company_id"): groups[r["peer_group_name"]].add(r["peer_company_id"])
    return groups

@router.get("/peers/{group_name}")
def peer_group(group_name: str, db: sqlite3.Connection = Depends(get_connection)):
    groups = membership(db)
    key = next((k for k in groups if k.casefold() == group_name.casefold()), None)
    if key is None: raise HTTPException(404, "Unknown peer group")
    if not {"company_id", "peer_group_name", "metric", "percentile_rank", "year"} <= columns(db, "peer_percentiles"):
        raise HTTPException(503, "Run Day 18 peer percentile generation first")
    out = []
    company_rows = {r["company_id"]: r for r in metrics(db)}
    for cid in sorted(groups[key]):
        ranks = records(db, """SELECT metric, value, percentile_rank FROM peer_percentiles
            WHERE company_id=? AND peer_group_name=? AND year=(
              SELECT MAX(year) FROM peer_percentiles WHERE company_id=? AND peer_group_name=?
            )""", (cid, key, cid, key))
        out.append({"company_id": cid, "company_name": company_rows.get(cid, {}).get("company_name"),
                    "percentiles": {r["metric"]: {"value": r["value"], "percentile_rank": r["percentile_rank"]} for r in ranks}})
    return {"group_name": key, "companies": out}

@router.get("/companies/{ticker}/peers/compare")
def compare(ticker: str, benchmark: str | None = None, db: sqlite3.Connection = Depends(get_connection)):
    cid = company(db, ticker)["id"]
    groups = membership(db)
    key = next((k for k, members in sorted(groups.items()) if cid in members), None)
    if key is None: raise HTTPException(404, "No peer group assigned")
    rows = {r["company_id"]: r for r in metrics(db)}
    members = [rows[x] for x in sorted(groups[key]) if x in rows]
    if not members: raise HTTPException(404, "Peer metrics unavailable")
    benchmark_id = benchmark or members[0]["company_id"]
    if benchmark_id not in {m["company_id"] for m in members}: raise HTTPException(400, "Benchmark not in peer group")
    def values(row):
        return {axis: row.get(LOOKUP[axis]) for axis in AXES}
    averages = {axis: (mean(v) if (v := [m[LOOKUP[axis]] for m in members if isinstance(m.get(LOOKUP[axis]), (int, float))]) else None) for axis in AXES}
    return {"peer_group": key, "axes": list(AXES), "company": {"company_id": cid, "values": values(rows[cid])},
            "peer_group_average": averages, "benchmark": {"company_id": benchmark_id, "values": values(rows[benchmark_id])}}
