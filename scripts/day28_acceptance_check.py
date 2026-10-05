"""Sprint 4 Day 28 — deterministic acceptance checks for local deliverables.

Run from the repository root:
    python scripts/day28_acceptance_check.py
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "nifty100.db"
SUMMARY = ROOT / "output" / "valuation_summary.xlsx"
FLAGS = ROOT / "output" / "valuation_flags.csv"
REQUIRED = ["company_id","company_name","sector","P/E","P/B","EV/EBITDA","FCF_yield_pct","5yr_median_PE","PE_vs_sector_median_pct","flag"]

def main() -> int:
    failures = []
    if not DB.exists():
        failures.append(f"missing database: {DB}")
    else:
        with sqlite3.connect(DB) as conn:
            companies = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
            groups = conn.execute("SELECT COUNT(DISTINCT peer_group_name) FROM peer_groups").fetchone()[0]
            metrics = conn.execute("SELECT COUNT(DISTINCT metric) FROM peer_percentiles").fetchone()[0]
        if companies != 92: failures.append(f"expected 92 companies, found {companies}")
        if groups != 11: failures.append(f"expected 11 peer groups, found {groups}")
        if metrics != 10: failures.append(f"expected 10 peer metrics, found {metrics}")

    if not SUMMARY.exists():
        failures.append(f"missing valuation workbook: {SUMMARY}")
    else:
        summary = pd.read_excel(SUMMARY)
        missing = [c for c in REQUIRED if c not in summary.columns]
        if missing: failures.append(f"valuation workbook missing columns: {missing}")
        if len(summary) != 92: failures.append(f"expected 92 valuation rows, found {len(summary)}")
        if summary["company_id"].nunique() != len(summary): failures.append("valuation workbook contains duplicate company_id values")

    if not FLAGS.exists():
        failures.append(f"missing valuation flags CSV: {FLAGS}")
    else:
        flags = pd.read_csv(FLAGS)
        if not flags.empty and not set(flags["flag"].dropna().unique()).issubset({"Caution","Discount"}):
            failures.append("valuation_flags.csv contains unexpected flag values")

    if failures:
        print("RESULT: FAIL")
        for failure in failures: print(f"- {failure}")
        return 1
    print("RESULT: PASS")
    print("92-company database, 11 peer groups, 10 peer metrics, and 92-row valuation workbook validated.")
    print("Valuation flags CSV contains only Caution/Discount rows.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
