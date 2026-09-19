"""Sprint 1 Day 05: robust loader for all 12 Nifty 100 source workbooks.

The source files are intentionally kept outside Git.  This loader normalises
the supplied Bluestock workbooks, preserves the 92-company master universe,
deduplicates annual records before inserting into UNIQUE(company_id, year)
tables, reshapes wide supplementary datasets, and records rejected/unmapped
source rows in the audit instead of failing an entire table transaction.
"""

from __future__ import annotations

import re
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
    "sectors.xlsx": "sectors",
    "peer_groups.xlsx": "peer_groups",
    "profitandloss.xlsx": "profitandloss",
    "balancesheet.xlsx": "balancesheet",
    "cashflow.xlsx": "cashflow",
    "analysis.xlsx": "analysis",
    "documents.xlsx": "documents",
    "prosandcons.xlsx": "prosandcons",
    "stock_prices.xlsx": "stock_prices",
    "financial_ratios.xlsx": "financial_ratios",
    "market_cap.xlsx": "market_cap",
}

EXPECTED = {
    "companies": (92, 92),
    "profitandloss": (1100, 1350),
    "balancesheet": (1000, 1375),
    "cashflow": (1000, 1250),
    "stock_prices": (5520, 5520),
}


def _canon(value: object) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def _normalise_company_id(value: object) -> str | None:
    if pd.isna(value):
        return None
    value = str(value).strip().upper()
    return value or None


def _normalise_year(value: object) -> int | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    match = re.search(r"(19\d{2}|20\d{2}|21\d{2})$", text)
    if match:
        return int(match.group(1))
    return normalize_year(value)


def _base(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [_canon(column) for column in frame.columns]
    if "company_id" in frame.columns:
        frame["company_id"] = frame["company_id"].map(_normalise_company_id)
    return frame


def _dedupe(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    frame = frame.dropna(subset=keys).copy()
    return frame.drop_duplicates(keys, keep="last").reset_index(drop=True)


def _records(table: str, source: pd.DataFrame, valid_companies: set[str]) -> tuple[pd.DataFrame, int]:
    data = _base(source)

    if table == "companies":
        output = pd.DataFrame(
            {
                "id": data["id"].map(_normalise_company_id),
                "company_name": data["company_name"].astype("string").str.strip(),
            }
        )
        for column in ["ticker", "bse_code", "nse_code", "isin", "sector", "industry", "website"]:
            output[column] = data[column] if column in data else None
        return _dedupe(output, ["id"]), 0

    if "company_id" in data:
        before = len(data)
        data = data[data["company_id"].isin(valid_companies)].copy()
        unmapped = before - len(data)
    else:
        unmapped = 0

    if table == "sectors":
        output = pd.DataFrame(
            {
                "id": data["id"],
                "company_id": data["company_id"],
                "sector": data.get("broad_sector"),
                "industry": data.get("sub_sector"),
            }
        )
        return _dedupe(output, ["company_id"]), unmapped

    if table == "peer_groups":
        output = pd.DataFrame(
            {
                "id": data["id"],
                "company_id": data["company_id"],
                "peer_group_name": data.get("peer_group_name"),
                "peer_company_id": None,
            }
        )
        return output.dropna(subset=["company_id"]).drop_duplicates(["id"]).reset_index(drop=True), unmapped

    if table in {"profitandloss", "balancesheet", "cashflow"}:
        data["year"] = data["year"].map(_normalise_year)

        if table == "profitandloss":
            output = data.rename(columns={"tax_percentage": "tax"}).reindex(
                columns=[
                    "id", "company_id", "year", "sales", "expenses",
                    "operating_profit", "opm_percentage", "other_income",
                    "interest", "depreciation", "profit_before_tax", "tax",
                    "net_profit", "eps",
                ]
            )
        elif table == "balancesheet":
            output = data.rename(columns={"other_asset": "other_assets"}).reindex(
                columns=[
                    "id", "company_id", "year", "equity_capital", "reserves",
                    "borrowings", "other_liabilities", "total_liabilities",
                    "fixed_assets", "investments", "other_assets", "total_assets",
                ]
            )
        else:
            output = data.rename(
                columns={
                    "operating_activity": "cash_from_operating_activity",
                    "investing_activity": "cash_from_investing_activity",
                    "financing_activity": "cash_from_financing_activity",
                }
            ).reindex(
                columns=[
                    "id", "company_id", "year",
                    "cash_from_operating_activity",
                    "cash_from_investing_activity",
                    "cash_from_financing_activity",
                    "net_cash_flow",
                ]
            )
        return _dedupe(output, ["company_id", "year"]), unmapped

    if table == "stock_prices":
        data = data.rename(columns={"date": "price_date"})
        data["price_date"] = pd.to_datetime(data["price_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        output = data.reindex(
            columns=["id", "company_id", "price_date", "open_price", "high_price", "low_price", "close_price", "volume"]
        )
        return _dedupe(output, ["company_id", "price_date"]), unmapped

    if table == "documents":
        output = pd.DataFrame(
            {
                "id": data["id"],
                "company_id": data["company_id"],
                "document_type": "Annual_Report",
                "document_url": data.get("annual_report"),
                "document_date": data["year"].map(_normalise_year) if "year" in data else None,
            }
        )
        return output.dropna(subset=["company_id"]).reset_index(drop=True), unmapped

    if table == "prosandcons":
        rows = []
        for _, row in data.iterrows():
            for item_type, column, offset in [("Pro", "pros", 0), ("Con", "cons", 1)]:
                if pd.notna(row.get(column)) and str(row[column]).strip():
                    rows.append(
                        {
                            "id": int(row["id"]) * 2 + offset,
                            "company_id": row["company_id"],
                            "item_type": item_type,
                            "description": row[column],
                        }
                    )
        return pd.DataFrame(rows), unmapped

    if table == "analysis":
        rows = []
        metrics = ["compounded_sales_growth", "compounded_profit_growth", "stock_price_cagr", "roe"]
        for _, row in data.iterrows():
            for index, metric in enumerate(metrics):
                if pd.notna(row.get(metric)):
                    rows.append(
                        {
                            "id": int(row["id"]) * 10 + index,
                            "company_id": row["company_id"],
                            "metric_name": metric,
                            "metric_value": None,
                            "metric_year": None,
                        }
                    )
        return pd.DataFrame(rows), unmapped

    if table == "financial_ratios":
        data["year"] = data["year"].map(_normalise_year)
        metric_columns = [c for c in data.columns if c not in {"id", "company_id", "year"}]
        rows = []
        for _, row in data.iterrows():
            for index, metric in enumerate(metric_columns):
                if pd.notna(row[metric]):
                    rows.append(
                        {
                            "id": int(row["id"]) * 100 + index,
                            "company_id": row["company_id"],
                            "year": row["year"],
                            "ratio_name": metric,
                            "ratio_value": row[metric],
                        }
                    )
        output = _dedupe(pd.DataFrame(rows), ["company_id", "year", "ratio_name"])
        return output, unmapped

    if table == "market_cap":
        data["year"] = data["year"].map(_normalise_year)
        output = data.rename(
            columns={
                "market_cap_crore": "market_cap",
                "enterprise_value_crore": "enterprise_value",
            }
        ).reindex(columns=["id", "company_id", "year", "market_cap", "enterprise_value"])
        return _dedupe(output, ["company_id", "year"]), unmapped

    raise ValueError(f"Unsupported table: {table}")


def _schema_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()]


def load_database() -> pd.DataFrame:
    PROJECT_ROOT.joinpath("output").mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    audits: list[dict[str, object]] = []

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        companies_source = load_excel(RAW_DATA_DIR / "companies.xlsx")
        companies, _ = _records("companies", companies_source, set())
        companies.to_sql("companies", connection, if_exists="append", index=False)
        valid_companies = set(companies["id"].dropna().astype(str))

        audits.append(
            {
                "source_file": "companies.xlsx",
                "target_table": "companies",
                "source_rows": len(companies_source),
                "loaded_rows": len(companies),
                "database_rows": len(companies),
                "unmapped_rows": 0,
                "status": "LOADED",
            }
        )

        for filename in FILES[1:]:
            table = TABLES[filename]
            path = RAW_DATA_DIR / filename
            if not path.exists():
                audits.append(
                    {
                        "source_file": filename,
                        "target_table": table,
                        "source_rows": 0,
                        "loaded_rows": 0,
                        "database_rows": 0,
                        "unmapped_rows": 0,
                        "status": "ERROR: missing source",
                    }
                )
                continue

            source = load_excel(path)
            try:
                records, unmapped = _records(table, source, valid_companies)
                columns = [c for c in records.columns if c in _schema_columns(connection, table)]
                records = records[columns].dropna(subset=["id"])
                records.to_sql(table, connection, if_exists="append", index=False)

                db_rows = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                lower, upper = EXPECTED.get(table, (None, None))
                status = "LOADED"
                if lower is not None and not lower <= db_rows <= upper:
                    status = f"WARNING: expected {lower}-{upper}, got {db_rows}"

                audits.append(
                    {
                        "source_file": filename,
                        "target_table": table,
                        "source_rows": len(source),
                        "loaded_rows": len(records),
                        "database_rows": db_rows,
                        "unmapped_rows": unmapped,
                        "status": status,
                    }
                )
            except Exception as exc:
                connection.rollback()
                audits.append(
                    {
                        "source_file": filename,
                        "target_table": table,
                        "source_rows": len(source),
                        "loaded_rows": 0,
                        "database_rows": int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]),
                        "unmapped_rows": 0,
                        "status": f"ERROR: {exc}",
                    }
                )

        fk_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        audits.append(
            {
                "source_file": "",
                "target_table": "",
                "source_rows": "",
                "loaded_rows": "",
                "database_rows": len(fk_errors),
                "unmapped_rows": "",
                "status": "FK_CHECK_0" if not fk_errors else f"FK_ERRORS:{len(fk_errors)}",
            }
        )

    audit = pd.DataFrame(audits)
    audit.to_csv(AUDIT_PATH, index=False)
    return audit


def main() -> None:
    audit = load_database()
    print(audit.to_string(index=False))
    print(f"\nAudit written to: {AUDIT_PATH}")
    print(f"Database written to: {DB_PATH}")


if __name__ == "__main__":
    main()
