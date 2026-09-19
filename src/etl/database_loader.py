"""Sprint 1 Day 05: load all 12 Excel datasets into SQLite.

The source workbooks must be present in data/raw. The loader applies the
Day 02 Excel header detection, maps source columns to the Day 04 schema,
loads parent tables before dependent tables, records an audit, and checks
SQLite foreign-key integrity.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.etl.loader import RAW_DATA_DIR, load_excel
from src.etl.normaliser import normalize_year

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"
DB_PATH = PROJECT_ROOT / "nifty100.db"
AUDIT_PATH = PROJECT_ROOT / "output" / "load_audit.csv"

FILES = [
    "companies.xlsx",
    "sectors.xlsx",
    "peer_groups.xlsx",
    "profitandloss.xlsx",
    "balancesheet.xlsx",
    "cashflow.xlsx",
    "analysis.xlsx",
    "documents.xlsx",
    "prosandcons.xlsx",
    "stock_prices.xlsx",
    "financial_ratios.xlsx",
    "market_cap.xlsx",
]

TABLES = {
    "companies.xlsx": "companies",
    "profitandloss.xlsx": "profitandloss",
    "balancesheet.xlsx": "balancesheet",
    "cashflow.xlsx": "cashflow",
    "analysis.xlsx": "analysis",
    "documents.xlsx": "documents",
    "prosandcons.xlsx": "prosandcons",
    "sectors.xlsx": "sectors",
    "stock_prices.xlsx": "stock_prices",
    "financial_ratios.xlsx": "financial_ratios",
    "market_cap.xlsx": "market_cap",
    "peer_groups.xlsx": "peer_groups",
}

EXPECTED = {
    "companies": (92, 92),
    "profitandloss": (1200, 1350),
    "balancesheet": (1250, 1375),
    "cashflow": (1125, 1250),
    "stock_prices": (5520, 5520),
}

ALIASES = {
    "company_id": ["company_id", "companyid", "company id", "id"],
    "year": ["year", "fy", "financial_year", "financial year"],
    "price_date": ["price_date", "date", "trade_date", "trading_date"],
    "close_price": ["close_price", "close", "closing_price", "close price"],
}


def _canonical(name: object) -> str:
    return str(name).strip().lower().replace("-", "_").replace(" ", "_")


def _apply_aliases(df: pd.DataFrame) -> pd.DataFrame:
    columns = {_canonical(c): c for c in df.columns}
    renamed = {}
    for target, aliases in ALIASES.items():
        for alias in aliases:
            key = _canonical(alias)
            if key in columns:
                renamed[columns[key]] = target
                break
    return df.rename(columns=renamed)


def _prepare(frame: pd.DataFrame, table: str) -> pd.DataFrame:
    df = _apply_aliases(frame.copy())
    df.columns = [_canonical(c) for c in df.columns]

    if "year" in df.columns:
        df["year"] = df["year"].map(normalize_year)

    if table == "stock_prices" and "price_date" in df.columns:
        df["price_date"] = pd.to_datetime(df["price_date"], errors="coerce").dt.strftime("%Y-%m-%d")

    if "id" not in df.columns:
        df.insert(0, "id", range(1, len(df) + 1))

    return df


def _schema_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return [row[1] for row in rows]


def _load_one(connection: sqlite3.Connection, filename: str) -> tuple[int, int, str]:
    path = RAW_DATA_DIR / filename
    table = TABLES[filename]

    if not path.exists():
        return 0, 0, f"ERROR: missing source file {path.name}"

    try:
        source = load_excel(path)
        prepared = _prepare(source, table)
        allowed = _schema_columns(connection, table)
        columns = [c for c in prepared.columns if c in allowed]

        required = {"companies": {"id", "company_name"}}.get(table, {"id"})
        missing = required - set(columns)
        if missing:
            return len(source), 0, f"ERROR: missing required columns {sorted(missing)}"

        # Drop rows that have no usable key before insertion.
        if "id" in prepared.columns:
            prepared = prepared[prepared["id"].notna()].copy()
        prepared = prepared[columns]

        prepared.to_sql(table, connection, if_exists="append", index=False)
        return len(source), len(prepared), "LOADED"
    except Exception as exc:
        connection.rollback()
        return len(source) if "source" in locals() else 0, 0, f"ERROR: {exc}"


def load_database() -> pd.DataFrame:
    PROJECT_ROOT.joinpath("output").mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        audit_rows = []
        for filename in FILES:
            table = TABLES[filename]
            source_rows, loaded_rows, status = _load_one(connection, filename)
            db_rows = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            expected = EXPECTED.get(table, (None, None))

            if status == "LOADED" and expected[0] is not None:
                in_range = expected[0] <= db_rows <= expected[1]
                if not in_range:
                    status = f"WARNING: expected {expected[0]}-{expected[1]}, got {db_rows}"

            audit_rows.append(
                {
                    "source_file": filename,
                    "target_table": table,
                    "source_rows": source_rows,
                    "loaded_rows": loaded_rows,
                    "database_rows": db_rows,
                    "status": status,
                }
            )

        fk_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        audit_rows.append(
            {
                "source_file": "",
                "target_table": "",
                "source_rows": "",
                "loaded_rows": "",
                "database_rows": len(fk_errors),
                "status": "FK_CHECK_0" if not fk_errors else f"FK_ERRORS:{len(fk_errors)}",
            }
        )

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(AUDIT_PATH, index=False)
    return audit


def main() -> None:
    audit = load_database()
    print(audit.to_string(index=False))
    print(f"\nAudit written to: {AUDIT_PATH}")
    print(f"Database written to: {DB_PATH}")


if __name__ == "__main__":
    main()
