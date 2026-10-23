"""Day 43 local performance and simultaneous-service integration runner.

Run from repository root: python -m scripts.day43_performance
Requires the populated db/nifty100.db and installed project dependencies.
"""
from __future__ import annotations
import concurrent.futures
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen
import httpx

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.getenv("N100_DB_PATH", str(ROOT / "db" / "nifty100.db"))).resolve()
OUTPUT = ROOT / "output" / "perf_notes.md"
TICKERS = ("TCS", "INFY", "HDFCBANK", "RELIANCE", "SUNPHARMA")
API = "http://127.0.0.1:8000"
UI = "http://127.0.0.1:8501"


def wait_http(url, process, timeout=35):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Service exited with code {process.returncode}: {url}")
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(.35)
    raise TimeoutError(f"Service did not become ready: {url}")


def ensure_free(port):
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError(f"Port {port} is already occupied; stop existing services first")


def screener_load():
    def call(_):
        started = time.perf_counter()
        response = httpx.get(API + "/api/v1/screener", params={"min_roe": 15}, timeout=10)
        response.raise_for_status()
        return {"seconds": round(time.perf_counter() - started, 4),
                "count": len(response.json()), "status": response.status_code}
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(call, range(10)))
    elapsed = time.perf_counter() - started
    return results, elapsed


def profile_loads():
    # Measures all four DB data helpers used by the profile screen, cold cache.
    from src.dashboard.utils.db import (get_companies, get_profile_ratios,
        get_profile_pl, get_profile_history, get_profile_pros_cons)
    results = []
    for ticker in TICKERS:
        for fn in (get_companies, get_profile_ratios, get_profile_pl,
                   get_profile_history, get_profile_pros_cons):
            fn.clear()
        started = time.perf_counter()
        companies = get_companies(str(DB))
        ratios = get_profile_ratios(ticker, 2024, str(DB))
        pl = get_profile_pl(ticker, str(DB))
        history = get_profile_history(ticker, str(DB))
        pros_cons = get_profile_pros_cons(ticker, str(DB))
        elapsed = time.perf_counter() - started
        results.append({"ticker": ticker, "seconds": round(elapsed, 4),
                        "data_present": not companies.empty and not pl.empty and not history.empty,
                        "ratios_rows": len(ratios), "pros_cons_rows": len(pros_cons)})
    return results


def query_plans():
    statements = {
        "ratios latest": ("SELECT * FROM financial_ratios WHERE company_id=? ORDER BY year DESC LIMIT 1", ("TCS",)),
        "P&L history": ("SELECT * FROM profitandloss WHERE company_id=? ORDER BY year", ("TCS",)),
        "market cap": ("SELECT * FROM market_cap WHERE company_id=? ORDER BY year DESC LIMIT 1", ("TCS",)),
        "profile history": ("""SELECT pl.year FROM profitandloss pl
            LEFT JOIN financial_ratios r ON r.company_id=pl.company_id AND r.year=pl.year
            LEFT JOIN balancesheet bs ON bs.company_id=pl.company_id AND bs.year=pl.year
            WHERE pl.company_id=? ORDER BY pl.year""", ("TCS",)),
    }
    with sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True) as db:
        return {name: [r[3] for r in db.execute("EXPLAIN QUERY PLAN " + sql, args)]
                for name, (sql, args) in statements.items()}


def run():
    if not DB.is_file():
        raise FileNotFoundError(f"Populated database required: {DB}")
    with sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True) as db:
        count = db.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    if count != 92:
        raise AssertionError(f"Expected 92 companies; found {count}")
    ensure_free(8000); ensure_free(8501)
    env = {**os.environ, "N100_DB_PATH": str(DB), "N100_SCREENER_SOURCE": "api",
           "N100_API_URL": API, "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false"}
    api = ui = None
    notes = [f"# Day 43 Performance & Integration Notes\n",
             f"Database: \\x60{DB}\\x60; company rows: {count}.\n",
             "Thresholds: ten concurrent screener requests in <10 seconds; five cold profile data loads each <3 seconds.\n"]
    try:
        api = subprocess.Popen([sys.executable, "-m", "uvicorn", "src.api.main:app",
                                "--host", "127.0.0.1", "--port", "8000"],
                               cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ui = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "src/dashboard/app.py",
                               "--server.address", "127.0.0.1", "--server.port", "8501",
                               "--server.headless", "true"], cwd=ROOT, env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_http(API + "/api/v1/health", api)
        wait_http(UI + "/_stcore/health", ui)
        health = httpx.get(API + "/api/v1/health", timeout=5).json()
        assert health["status"] == "ok" and health["db_row_counts"]["companies"] == 92
        notes.append("## Simultaneous startup\nFastAPI :8000 and Streamlit :8501: PASS (both health checks HTTP 200).\n")
        results, wall = screener_load()
        load_ok = wall < 10 and len(results) == 10 and all(r["status"] == 200 for r in results)
        notes.append(f"## Concurrent screener\nTotal wall time: {wall:.4f}s; target <10s: {'PASS' if load_ok else 'FAIL'}.\n")
        notes.append("| Call | Seconds | Rows | HTTP |\n|---:|---:|---:|---:|")
        notes += [f"| {i} | {r['seconds']} | {r['count']} | {r['status']} |" for i, r in enumerate(results, 1)]
        notes.append("\n## Five Company Profile cold data loads\nThese timings cover data helpers, not browser rendering.\n")
        notes.append("| Ticker | Seconds | Data present | Target |\n|---|---:|---|---|")
        profiles = profile_loads()
        notes += [f"| {r['ticker']} | {r['seconds']} | {r['data_present']} | {'PASS' if r['seconds'] < 3 and r['data_present'] else 'FAIL'} |" for r in profiles]
        plans = query_plans()
        notes.append("\n## SQLite query plans\n")
        notes += [f"- {name}: \\x60{' ; '.join(plan)}\\x60" for name, plan in plans.items()]
        notes.append("\n## Bottlenecks and limitations\n")
        notes.append("- Existing schema includes composite company/year indexes for P&L, balance sheet, cash flow, ratios and market cap; inspect plans before adding duplicate indexes.")
        notes.append("- Streamlit HTTP health confirms server readiness, not interactive page rendering. Manually open :8501, select Screener and Company Profile, verify values, and record browser rendering separately.")
        notes.append("- API-backed screener is enabled for the launched Streamlit process; compare displayed IDs with the API using identical enabled filters.")
        notes.append("- Profile benchmark uses cold cached data helpers; full browser render timing needs separate browser instrumentation.")
        success = load_ok and all(r["seconds"] < 3 and r["data_present"] for r in profiles)
        notes.append(f"\nOverall automated performance gates: {'PASS' if success else 'FAIL'}. Manual UI gate: PENDING.\n")
        return 0 if success else 1
    except Exception as exc:
        notes.append(f"\nExecution error: {type(exc).__name__}: {exc}\n")
        return 1
    finally:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text("\n".join(notes) + "\n", encoding="utf-8")
        for proc in (ui, api):
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.wait()


if __name__ == "__main__":
    raise SystemExit(run())
