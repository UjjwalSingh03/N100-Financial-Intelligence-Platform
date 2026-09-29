"""Day 12 financial ratio table population."""

from __future__ import annotations

import argparse
import math
import sqlite3
from pathlib import Path
from typing import Any

from src.analytics.cagr import cagr_for_window
from src.analytics.cash_flow import free_cash_flow, fcf_conversion_rate
from src.analytics.ratios import (
    asset_turnover,
    debt_to_equity,
    interest_coverage_ratio,
    net_profit_margin,
    operating_profit_margin,
    return_on_equity,
)

KPI_COLUMNS = [
    "net_profit_margin_pct", "operating_profit_margin_pct", "return_on_equity_pct",
    "debt_to_equity", "interest_coverage", "asset_turnover", "free_cash_flow_cr",
    "capex_cr", "earnings_per_share", "book_value_per_share",
    "dividend_payout_ratio_pct", "total_debt_cr", "cash_from_operations_cr",
    "revenue_cagr_5yr", "pat_cagr_5yr", "eps_cagr_5yr", "composite_quality_score",
]


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def load(conn: sqlite3.Connection, table: str, columns: list[str]) -> dict[tuple[str, int], dict[str, Any]]:
    available = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    selected = [c for c in columns if c in available]
    out = {}
    for row in conn.execute(f"SELECT {', '.join(selected)} FROM {table}"):
        item = dict(zip(selected, row))
        cid = str(item.get("company_id") or "").strip()
        try:
            year = int(str(item.get("year"))[:4])
        except (TypeError, ValueError):
            continue
        out[(cid, year)] = item
    return out


def series(rows: dict[tuple[str, int], dict[str, Any]], cid: str, field: str) -> list[Any]:
    return [v[field] for (c, _), v in sorted(rows.items()) if c == cid and number(v.get(field)) is not None]


def quality_score(npm: float | None, roe: float | None, de: float | None, icr: float | None, fcf_conv: float | None) -> float | None:
    values = []
    if npm is not None: values.append(max(0, min(100, npm * 4)))
    if roe is not None: values.append(max(0, min(100, roe * 2)))
    if de is not None: values.append(max(0, min(100, 100 - de * 20)))
    if icr is not None: values.append(max(0, min(100, icr * 20)))
    if fcf_conv is not None: values.append(max(0, min(100, fcf_conv)))
    return sum(values) / len(values) if values else None


def create_table(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS financial_ratios")
    conn.execute("""
        CREATE TABLE financial_ratios (
            id INTEGER PRIMARY KEY,
            company_id TEXT NOT NULL,
            year INTEGER NOT NULL,
            net_profit_margin_pct REAL,
            operating_profit_margin_pct REAL,
            return_on_equity_pct REAL,
            debt_to_equity REAL,
            interest_coverage REAL,
            asset_turnover REAL,
            free_cash_flow_cr REAL,
            capex_cr REAL,
            earnings_per_share REAL,
            book_value_per_share REAL,
            dividend_payout_ratio_pct REAL,
            total_debt_cr REAL,
            cash_from_operations_cr REAL,
            revenue_cagr_5yr REAL,
            pat_cagr_5yr REAL,
            eps_cagr_5yr REAL,
            composite_quality_score REAL,
            UNIQUE(company_id, year),
            FOREIGN KEY(company_id) REFERENCES companies(id)
        )
    """)
    conn.execute("CREATE INDEX idx_ratios_company_year ON financial_ratios(company_id, year)")


def populate(db_path: Path) -> int:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        pnl = load(conn, "profitandloss", ["company_id","year","sales","operating_profit","opm_percentage","other_income","interest","net_profit","eps"])
        bs = load(conn, "balancesheet", ["company_id","year","equity_capital","reserves","borrowings","total_assets","investments"])
        cf = load(conn, "cashflow", ["company_id","year","cash_from_operating_activity","cash_from_investing_activity"])
        create_table(conn)
        rows = []
        for cid, year in sorted(set(pnl) | set(bs) | set(cf)):
            p, b, c = pnl.get((cid, year), {}), bs.get((cid, year), {}), cf.get((cid, year), {})
            sales, profit = number(p.get("sales")), number(p.get("net_profit"))
            op, equity = number(p.get("operating_profit")), number(b.get("equity_capital"))
            reserves, debt = number(b.get("reserves")), number(b.get("borrowings"))
            assets, cfo = number(b.get("total_assets")), number(c.get("cash_from_operating_activity"))
            cfi = number(c.get("cash_from_investing_activity"))
            npm = net_profit_margin(profit, sales)
            opm = operating_profit_margin(op, sales, number(p.get("opm_percentage")))
            roe = return_on_equity(profit, equity, reserves)
            de = debt_to_equity(debt, equity, reserves)
            icr = interest_coverage_ratio(op, number(p.get("other_income")), number(p.get("interest")))
            turnover = asset_turnover(sales, assets)
            fcf = free_cash_flow(cfo, cfi)
            fcf_conv = fcf_conversion_rate(fcf, op)
            revenue_cagr = cagr_for_window(series(pnl, cid, "sales"), 5).value
            pat_cagr = cagr_for_window(series(pnl, cid, "net_profit"), 5).value
            eps_cagr = cagr_for_window(series(pnl, cid, "eps"), 5).value
            rows.append((
                cid, year, npm, opm, roe, de, icr, turnover, fcf,
                abs(cfi) if cfi is not None else None, number(p.get("eps")),
                None, None, debt, cfo, revenue_cagr, pat_cagr, eps_cagr,
                quality_score(npm, roe, de, icr, fcf_conv),
            ))
        conn.executemany("""
            INSERT INTO financial_ratios (
                company_id, year, net_profit_margin_pct, operating_profit_margin_pct,
                return_on_equity_pct, debt_to_equity, interest_coverage, asset_turnover,
                free_cash_flow_cr, capex_cr, earnings_per_share, book_value_per_share,
                dividend_payout_ratio_pct, total_debt_cr, cash_from_operations_cr,
                revenue_cagr_5yr, pat_cagr_5yr, eps_cagr_5yr, composite_quality_score
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, rows)
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
        if count < 1100:
            raise RuntimeError(f"financial_ratios row count is {count}; expected >= 1100")
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("foreign_key_check failed")
        return count
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("db/nifty100.db"))
    args = parser.parse_args()
    print(f"financial_ratios rows: {populate(args.db)}")


if __name__ == "__main__":
    main()
