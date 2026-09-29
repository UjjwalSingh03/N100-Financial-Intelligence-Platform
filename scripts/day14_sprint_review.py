"""Day 14 Sprint 2 validation and review runner."""
from __future__ import annotations
import argparse
import re
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "db" / "nifty100.db"
EDGE_LOG = ROOT / "output" / "ratio_edge_cases.log"
CAPITAL_ALLOCATION = ROOT / "output" / "capital_allocation.csv"
KPI_COLUMNS = [
    "net_profit_margin_pct","operating_profit_margin_pct","return_on_equity_pct",
    "debt_to_equity","interest_coverage","asset_turnover","free_cash_flow_cr",
    "capex_cr","earnings_per_share","book_value_per_share",
    "dividend_payout_ratio_pct","total_debt_cr","cash_from_operations_cr",
    "revenue_cagr_5yr","pat_cagr_5yr","eps_cagr_5yr","composite_quality_score",
]

def latest_screener(conn):
    return conn.execute("""
        WITH latest AS (
            SELECT company_id, MAX(year) AS year FROM financial_ratios GROUP BY company_id
        )
        SELECT r.company_id, r.year, r.return_on_equity_pct, r.debt_to_equity
        FROM financial_ratios r
        JOIN latest l ON l.company_id=r.company_id AND l.year=r.year
        WHERE r.return_on_equity_pct > 15 AND r.debt_to_equity < 1
        ORDER BY r.return_on_equity_pct DESC, r.company_id
    """).fetchall()

def check_edge_log(path):
    if not path.exists():
        return False, 0, ["ratio_edge_cases.log does not exist"]
    count, errors = 0, []
    category = re.compile(r"category=(data source issue|version difference|formula discrepancy)")
    reason = re.compile(r"reason=\S")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or not (line.startswith("ROCE |") or line.startswith("ROE |")):
            continue
        count += 1
        if not category.search(line):
            errors.append(f"missing/invalid category: {line}")
        if not reason.search(line):
            errors.append(f"missing explanation: {line}")
    return not errors, count, errors

def run_formula_tests():
    targets = ["tests/analytics/test_ratios.py","tests/analytics/test_cagr.py","tests/analytics/test_cash_flow.py"]
    result = subprocess.run(["python","-m","pytest","-q",*targets], cwd=ROOT, text=True, capture_output=True)
    match = re.search(r"(\d+) passed", result.stdout)
    return result.returncode, int(match.group(1)) if match else 0, result.stdout + result.stderr

def review(db_path):
    if not db_path.exists():
        print(f"BLOCKED: database not found: {db_path}")
        return 2
    test_code, passed, test_output = run_formula_tests()
    print(f"Formula tests: {passed} passed; pytest exit={test_code}")
    conn = sqlite3.connect(db_path)
    try:
        row_count = conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
        columns = {r[1] for r in conn.execute("PRAGMA table_info(financial_ratios)")}
        null_only = [c for c in KPI_COLUMNS if c not in columns or conn.execute(
            f"SELECT COUNT(*) FROM financial_ratios WHERE {c} IS NOT NULL").fetchone()[0] == 0]
        fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        screen = latest_screener(conn)
        print(f"financial_ratios rows: {row_count}")
        print(f"Null-only KPI columns: {null_only}")
        print(f"Foreign-key errors: {len(fk_errors)}")
        print(f"Screener ROE > 15%, D/E < 1: {len(screen)} companies")
        for row in screen[:5]:
            print(f"  {row[0]} | {row[1]} | ROE={row[2]:.2f} | D/E={row[3]:.2f}")
        edge_ok, anomaly_count, edge_errors = check_edge_log(EDGE_LOG)
        print(f"Edge-case log anomalies: {anomaly_count}; documented={edge_ok}")
        capital_ok = CAPITAL_ALLOCATION.exists()
        blockers = []
        if row_count < 1100: blockers.append(f"financial_ratios has {row_count} rows; expected >= 1100")
        if null_only: blockers.append("null-only KPI columns: " + ", ".join(null_only))
        if fk_errors: blockers.append("foreign_key_check returned rows")
        if test_code != 0 or passed < 20: blockers.append("formula-test gate failed")
        if not 15 <= len(screen) <= 50: blockers.append(f"screener count {len(screen)} outside 15-50")
        if not edge_ok: blockers.append("ratio_edge_cases.log has undocumented/invalid anomaly entries")
        if not capital_ok: blockers.append("output/capital_allocation.csv is missing")
        if blockers:
            print("\nDAY 14 STATUS: BLOCKED")
            for item in blockers: print(f"- {item}")
            if test_code != 0 or passed < 20: print(test_output)
            return 1
        print("\nDAY 14 STATUS: READY FOR TEAM-LEAD REVIEW")
        return 0
    finally:
        conn.close()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--db",type=Path,default=DEFAULT_DB)
    raise SystemExit(review(parser.parse_args().db))

if __name__=="__main__":
    main()
