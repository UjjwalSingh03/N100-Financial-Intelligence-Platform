"""Generate output/capital_allocation.csv from nifty100.db for Sprint 2 Day 11."""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path

from src.analytics.cash_flow import capital_allocation_pattern, cfo_quality_score


def _quality_by_company_year(
    rows: list[sqlite3.Row],
) -> dict[tuple[str, int], float | None]:
    grouped: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        grouped.setdefault(row["company_id"], []).append(row)

    result: dict[tuple[str, int], float | None] = {}
    for company_rows in grouped.values():
        ordered = sorted(company_rows, key=lambda r: r["year"])
        for index, row in enumerate(ordered):
            window = ordered[max(0, index - 4): index + 1]
            ratios = [
                {"cfo": item["cfo"], "pat": item["pat"]}
                for item in window
            ]
            result[(row["company_id"], row["year"])] = cfo_quality_score(ratios)
    return result


def generate(db_path: str, output_path: str) -> int:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT
            cf.company_id,
            cf.year,
            cf.cash_from_operating_activity AS cfo,
            cf.cash_from_investing_activity AS cfi,
            cf.cash_from_financing_activity AS cff,
            pnl.net_profit AS pat
        FROM cashflow AS cf
        LEFT JOIN profitandloss AS pnl
          ON pnl.company_id = cf.company_id
         AND pnl.year = cf.year
        ORDER BY cf.company_id, cf.year
        """
    ).fetchall()
    con.close()

    quality = _quality_by_company_year(rows)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "company_id",
                "year",
                "cfo_sign",
                "cfi_sign",
                "cff_sign",
                "pattern_label",
            ],
        )
        writer.writeheader()
        for row in rows:
            score = quality[(row["company_id"], row["year"])]
            writer.writerow(
                {
                    "company_id": row["company_id"],
                    "year": row["year"],
                    "cfo_sign": "+" if row["cfo"] > 0 else "-" if row["cfo"] < 0 else "0",
                    "cfi_sign": "+" if row["cfi"] > 0 else "-" if row["cfi"] < 0 else "0",
                    "cff_sign": "+" if row["cff"] > 0 else "-" if row["cff"] < 0 else "0",
                    "pattern_label": capital_allocation_pattern(
                        row["cfo"], row["cfi"], row["cff"], score
                    ),
                }
            )
    print(f"Generated {path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="db/nifty100.db")
    parser.add_argument("--output", default="output/capital_allocation.csv")
    args = parser.parse_args()
    return generate(args.db, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
