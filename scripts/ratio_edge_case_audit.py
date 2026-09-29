"""Day 13: audit Financials carve-out and source ROCE/ROE values.

The ratio engine remains authoritative for analytics. Source ROCE/ROE values are
treated as display/reference fields and are never substituted into computed KPIs.
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
from pathlib import Path
from typing import Any

from src.analytics.ratios import high_leverage_flag, return_on_capital_employed, return_on_equity

LOG_PATH = Path("output/ratio_edge_cases.log")
ROCE_THRESHOLD_PCT_POINTS = 5.0
logger = logging.getLogger(__name__)


def _num(value: Any) -> float | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        value = float(value)
        return value if value == value and abs(value) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _first_column(columns: set[str], *names: str) -> str | None:
    lowered = {c.casefold(): c for c in columns}
    for name in names:
        if name.casefold() in lowered:
            return lowered[name.casefold()]
    return None


def _category(source: float | None, calculated: float | None) -> tuple[str, str]:
    """Assign a conservative category without changing the analytics value.

    A formula discrepancy is used only when the source is numerically valid and
    the calculated value is available but materially different. Otherwise the
    entry is treated as a source-data issue. Version differences are reserved
    for an explicit version marker in the source dataset.
    """
    if source is None:
        return "data source issue", "source value is missing or non-numeric"
    if calculated is None:
        return "data source issue", "required inputs for the engine calculation are missing/invalid"
    return "formula discrepancy", "source value differs materially from the engine calculation"


def audit(db_path: Path, log_path: Path = LOG_PATH) -> dict[str, int]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    log_path.parent.mkdir(parents=True, exist_ok=True)
    counts = {"financials": 0, "roce_anomalies": 0, "roe_anomalies": 0}
    try:
        company_cols = _columns(conn, "companies")
        broad_sector_col = _first_column(company_cols, "broad_sector")
        roce_source_col = _first_column(company_cols, "roce_percentage", "roce_percent", "roce")
        roe_source_col = _first_column(company_cols, "roe_percentage", "roe_percent", "roe")
        sector_col = _first_column(company_cols, "sector")

        # A schema without these source columns is still audited and reported.
        if roce_source_col is None:
            logger.warning("companies table has no ROCE source column")
        if roe_source_col is None:
            logger.warning("companies table has no ROE source column")

        pnl_cols = _columns(conn, "profitandloss")
        bs_cols = _columns(conn, "balancesheet")
        required_pnl = ["company_id", "year", "operating_profit", "net_profit"]
        required_bs = ["company_id", "year", "equity_capital", "reserves", "borrowings"]
        if not all(c in pnl_cols for c in required_pnl) or not all(c in bs_cols for c in required_bs):
            raise RuntimeError("normalized P&L/Balance Sheet schema is missing ROCE/ROE inputs")

        select_company = [
            "c.id AS company_id",
            f"c.{broad_sector_col} AS broad_sector" if broad_sector_col else "NULL AS broad_sector",
            f"c.{sector_col} AS sector" if sector_col else "NULL AS sector",
            f"c.{roce_source_col} AS source_roce" if roce_source_col else "NULL AS source_roce",
            f"c.{roe_source_col} AS source_roe" if roe_source_col else "NULL AS source_roe",
        ]
        query = f"""
            SELECT {", ".join(select_company)}, p.year,
                   p.operating_profit, p.net_profit,
                   b.equity_capital, b.reserves, b.borrowings
            FROM companies c
            JOIN profitandloss p ON p.company_id = c.id
            JOIN balancesheet b ON b.company_id = c.id AND b.year = p.year
            ORDER BY c.id, p.year
        """

        with log_path.open("w", encoding="utf-8") as fh:
            fh.write("# Day 13 — Ratio Edge Case Audit\n")
            fh.write("# ROCE anomalies: absolute source-vs-engine difference > 5 percentage points.\n")
            fh.write("# ROE source values are logged for review; engine ROE remains authoritative for analytics.\n")
            fh.write("# Categories: data source issue | version difference | formula discrepancy.\n\n")

            for row in conn.execute(query):
                broad_sector = str(row["broad_sector"] or "").strip()
                sector = str(row["sector"] or "").strip()
                is_financials = broad_sector.casefold() == "financials"
                if is_financials:
                    counts["financials"] += 1

                de = None
                equity = _num(row["equity_capital"])
                reserves = _num(row["reserves"])
                debt = _num(row["borrowings"])
                if debt is not None and equity is not None and reserves is not None and equity + reserves > 0:
                    de = debt / (equity + reserves)

                flag = high_leverage_flag(de, broad_sector)
                if is_financials and flag:
                    raise AssertionError(f"Financials leverage warning was not suppressed: {row['company_id']}")

                roce = return_on_capital_employed(
                    row["operating_profit"], row["equity_capital"], row["reserves"], row["borrowings"]
                )
                roe = return_on_equity(row["net_profit"], row["equity_capital"], row["reserves"])
                source_roce = _num(row["source_roce"])
                source_roe = _num(row["source_roe"])

                if source_roce is not None and roce is not None and abs(source_roce - roce) > ROCE_THRESHOLD_PCT_POINTS:
                    category, reason = _category(source_roce, roce)
                    counts["roce_anomalies"] += 1
                    fh.write(
                        f"ROCE | company_id={row['company_id']} | year={row['year']} | "
                        f"broad_sector={broad_sector or 'unknown'} | source={source_roce:.6f} | "
                        f"engine={roce:.6f} | difference={abs(source_roce-roce):.6f}pp | "
                        f"category={category} | reason={reason}\n"
                    )

                if source_roe is not None and roe is not None and abs(source_roe - roe) > ROCE_THRESHOLD_PCT_POINTS:
                    category, reason = _category(source_roe, roe)
                    counts["roe_anomalies"] += 1
                    fh.write(
                        f"ROE | company_id={row['company_id']} | year={row['year']} | "
                        f"broad_sector={broad_sector or 'unknown'} | source={source_roe:.6f} | "
                        f"engine={roe:.6f} | difference={abs(source_roe-roe):.6f}pp | "
                        f"category={category} | reason={reason}\n"
                    )

        # Keep an explicit review summary so version differences are not
        # silently asserted without evidence.
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write("\n# Review guidance\n")
            fh.write("# data source issue: malformed/missing source value or missing engine inputs.\n")
            fh.write("# formula discrepancy: both values are valid but materially differ under the engine formula.\n")
            fh.write("# version difference: assign only when the source/version metadata confirms a historical formula/version change.\n")
        return counts
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("db/nifty100.db"))
    parser.add_argument("--log", type=Path, default=LOG_PATH)
    args = parser.parse_args()
    counts = audit(args.db, args.log)
    print(
        f"Financials rows: {counts['financials']}; "
        f"ROCE anomalies: {counts['roce_anomalies']}; ROE anomalies: {counts['roe_anomalies']}"
    )


if __name__ == "__main__":
    main()
