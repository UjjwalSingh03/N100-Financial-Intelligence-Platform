"""Sprint 1 Day 05: robust loader for all 12 Nifty 100 source workbooks.

The loader normalises the supplied Bluestock workbooks, preserves the 92-company
master universe, resolves child-company identifiers against the master company
aliases, deduplicates annual records before inserting into UNIQUE tables, and
records unmapped source rows in the audit.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd

from src.etl.loader import RAW_DATA_DIR, load_excel
from src.etl.normaliser import normalize_ticker, normalize_year

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"
DB_PATH = PROJECT_ROOT / "nifty100.db"
AUDIT_PATH = PROJECT_ROOT / "output" / "load_audit.csv"

FILES = [
    "companies.xlsx", "sectors.xlsx", "peer_groups.xlsx", "profitandloss.xlsx",
    "balancesheet.xlsx", "cashflow.xlsx", "analysis.xlsx", "documents.xlsx",
    "prosandcons.xlsx", "stock_prices.xlsx", "financial_ratios.xlsx", "market_cap.xlsx",
]

TABLES = {
    "companies.xlsx": "companies", "sectors.xlsx": "sectors", "peer_groups.xlsx": "peer_groups",
    "profitandloss.xlsx": "profitandloss", "balancesheet.xlsx": "balancesheet",
    "cashflow.xlsx": "cashflow", "analysis.xlsx": "analysis", "documents.xlsx": "documents",
    "prosandcons.xlsx": "prosandcons", "stock_prices.xlsx": "stock_prices",
    "financial_ratios.xlsx": "financial_ratios", "market_cap.xlsx": "market_cap",
}

EXPECTED = {
    "companies": (92, 92), "profitandloss": (1100, 1350), "balancesheet": (1000, 1375),
    "cashflow": (1000, 1250), "stock_prices": (5520, 5520),
}


def _canon(value: object) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def _normalise_company_id(value: object) -> str | None:
    """Normalise ticker/code-like company identifiers consistently."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    # Excel can turn numeric identifiers into values such as 500325.0.
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    normalized = normalize_ticker(text)
    return normalized or None


def _normalise_alias(value: object) -> str | None:
    """Create a case/whitespace-insensitive alias key."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return re.sub(r"\s+", " ", text).upper()


def _normalise_year(value: object) -> int | None:
    if value is None or pd.isna(value):
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


def _build_company_aliases(companies: pd.DataFrame) -> dict[str, str]:
    """Map source identifiers/names to the canonical companies.id value."""
    aliases: dict[str, str] = {}
    collisions: set[str] = set()
    alias_columns = ["id", "ticker", "nse_code", "bse_code", "isin", "company_name"]

    for _, row in companies.iterrows():
        canonical = _normalise_company_id(row.get("id"))
        if not canonical:
            continue
        for column in alias_columns:
            raw = row.get(column)
            alias = _normalise_alias(raw)
            if not alias:
                continue
            previous = aliases.get(alias)
            if previous is not None and previous != canonical:
                collisions.add(alias)
            else:
                aliases[alias] = canonical

            ticker_alias = _normalise_alias(_normalise_company_id(raw))
            if ticker_alias and ticker_alias not in collisions:
                previous = aliases.get(ticker_alias)
                if previous is None or previous == canonical:
                    aliases[ticker_alias] = canonical

    for alias in collisions:
        aliases.pop(alias, None)
    return aliases


def _resolve_company_ids(frame: pd.DataFrame, aliases: dict[str, str]) -> tuple[pd.DataFrame, int]:
    if "company_id" not in frame.columns:
        return frame, 0

    resolved = frame.copy()
    original = resolved["company_id"]
    resolved["company_id"] = original.map(lambda value: aliases.get(_normalise_alias(value)))
    unresolved = int(resolved["company_id"].isna().sum())
    return resolved, unresolved


def _records(table: str, source: pd.DataFrame, aliases: dict[str, str]) -> tuple[pd.DataFrame, int]:
    data = _base(source)

    if table == "companies":
        output = pd.DataFrame({
            "id": data["id"].map(_normalise_company_id),
            "company_name": data["company_name"].astype("string").str.strip(),
        })
        for column in ["ticker", "bse_code", "nse_code", "isin", "sector", "industry", "website"]:
            output[column] = data[column] if column in data else None
        return _dedupe(output, ["id"]), 0

    data, unmapped = _resolve_company_ids(data, aliases)
    data = data.dropna(subset=["company_id"]).copy()

    if table == "sectors":
        output = pd.DataFrame({"id": data["id"], "company_id": data["company_id"],
                               "sector": data.get("broad_sector"), "industry": data.get("sub_sector")})
        return _dedupe(output, ["company_id"]), unmapped

    if table == "peer_groups":
        output = pd.DataFrame({"id": data["id"], "company_id": data["company_id"],
                               "peer_group_name": data.get("peer_group_name"), "peer_company_id": None})
        return output.drop_duplicates(["id"]).reset_index(drop=True), unmapped

    if table in {"profitandloss", "balancesheet", "cashflow"}:
        data["year"] = data["year"].map(_normalise_year)
        if table == "profitandloss":
            output = data.rename(columns={"tax_percentage": "tax"}).reindex(
                columns=["id","company_id","year","sales","expenses","operating_profit","opm_percentage",
                         "other_income","interest","depreciation","profit_before_tax","tax","net_profit","eps"])
        elif table == "balancesheet":
            output = data.rename(columns={"other_asset": "other_assets"}).reindex(
                columns=["id","company_id","year","equity_capital","reserves","borrowings",
                         "other_liabilities","total_liabilities","fixed_assets","investments",
                         "other_assets","total_assets"])
        else:
            output = data.rename(columns={
                "operating_activity":"cash_from_operating_activity",
                "investing_activity":"cash_from_investing_activity",
                "financing_activity":"cash_from_financing_activity",
            }).reindex(columns=["id","company_id","year","cash_from_operating_activity",
                                 "cash_from_investing_activity","cash_from_financing_activity","net_cash_flow"])
        return _dedupe(output, ["company_id","year"]), unmapped

    if table == "stock_prices":
        data = data.rename(columns={"date":"price_date"})
        data["price_date"] = pd.to_datetime(data["price_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        output = data.reindex(columns=["id","company_id","price_date","open_price","high_price","low_price","close_price","volume"])
        return _dedupe(output, ["company_id","price_date"]), unmapped

    if table == "documents":
        output = pd.DataFrame({
            "id": data["id"], "company_id": data["company_id"], "document_type": "Annual_Report",
            "document_url": data.get("annual_report"),
            "document_date": data["year"].map(_normalise_year) if "year" in data else None,
        })
        return output.reset_index(drop=True), unmapped

    if table == "prosandcons":
        rows = []
        for _, row in data.iterrows():
            for item_type, column, offset in [("Pro","pros",0),("Con","cons",1)]:
                if pd.notna(row.get(column)) and str(row[column]).strip():
                    rows.append({"id": int(row["id"])*2+offset, "company_id": row["company_id"],
                                 "item_type": item_type, "description": row[column]})
        return pd.DataFrame(rows), unmapped

    if table == "analysis":
        rows = []
        for _, row in data.iterrows():
            for index, metric in enumerate(["compounded_sales_growth","compounded_profit_growth","stock_price_cagr","roe"]):
                if pd.notna(row.get(metric)):
                    rows.append({"id": int(row["id"])*10+index, "company_id": row["company_id"],
                                 "metric_name": metric, "metric_value": row[metric],
                                 "metric_year": _normalise_year(row.get("year")) if pd.notna(row.get("year")) else None})
        return pd.DataFrame(rows), unmapped

    if table == "financial_ratios":
        data["year"] = data["year"].map(_normalise_year)
        metric_columns = [c for c in data.columns if c not in {"id","company_id","year"}]
        rows = []
        for _, row in data.iterrows():
            for index, metric in enumerate(metric_columns):
                if pd.notna(row[metric]):
                    rows.append({"id": int(row["id"])*100+index, "company_id": row["company_id"],
                                 "year": row["year"], "ratio_name": metric, "ratio_value": row[metric]})
        return _dedupe(pd.DataFrame(rows), ["company_id","year","ratio_name"]), unmapped

    if table == "market_cap":
        data["year"] = data["year"].map(_normalise_year)
        output = data.rename(columns={"market_cap_crore":"market_cap","enterprise_value_crore":"enterprise_value"}).reindex(
            columns=["id","company_id","year","market_cap","enterprise_value"])
        return _dedupe(output, ["company_id","year"]), unmapped

    raise ValueError(f"Unsupported table: {table}")


def _resolve_source(logical_name: str) -> Path | None:
    exact = RAW_DATA_DIR / logical_name
    if exact.exists():
        return exact
    matches = sorted(path for path in RAW_DATA_DIR.glob(f"*{logical_name}") if path.is_file())
    if len(matches) == 1:
        return matches[0]
    if not matches:
        return None
    raise RuntimeError(f"Multiple source files match {logical_name}: " + ", ".join(path.name for path in matches))


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

        companies_path = _resolve_source("companies.xlsx")
        if companies_path is None:
            raise FileNotFoundError("Missing source workbook: companies.xlsx")
        companies_source = load_excel(companies_path)
        companies, _ = _records("companies", companies_source, {})
        companies.to_sql("companies", connection, if_exists="append", index=False)
        aliases = _build_company_aliases(companies)
        valid_companies = set(companies["id"].dropna().astype(str))

        audits.append({"source_file": companies_path.name, "target_table":"companies",
                       "source_rows":len(companies_source),"loaded_rows":len(companies),
                       "database_rows":len(companies),"unmapped_rows":0,"status":"LOADED"})

        for filename in FILES[1:]:
            table = TABLES[filename]
            path = _resolve_source(filename)
            if path is None:
                audits.append({"source_file":filename,"target_table":table,"source_rows":0,
                               "loaded_rows":0,"database_rows":0,"unmapped_rows":0,"status":"ERROR: missing source"})
                continue

            source = load_excel(path)
            try:
                records, unmapped = _records(table, source, aliases)
                columns = [c for c in records.columns if c in _schema_columns(connection, table)]
                records = records[columns].dropna(subset=["id"])
                records.to_sql(table, connection, if_exists="append", index=False)
                db_rows = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                lower, upper = EXPECTED.get(table, (None, None))
                status = "LOADED"
                if lower is not None and not lower <= db_rows <= upper:
                    status = f"WARNING: expected {lower}-{upper}, got {db_rows}"
                audits.append({"source_file":path.name,"target_table":table,"source_rows":len(source),
                               "loaded_rows":len(records),"database_rows":db_rows,
                               "unmapped_rows":unmapped,"status":status})
            except Exception as exc:
                connection.rollback()
                audits.append({"source_file":filename,"target_table":table,"source_rows":len(source),
                               "loaded_rows":0,"database_rows":int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]),
                               "unmapped_rows":0,"status":f"ERROR: {exc}"})

        fk_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        audits.append({"source_file":"","target_table":"","source_rows":"","loaded_rows":"",
                       "database_rows":len(fk_errors),"unmapped_rows":"",
                       "status":"FK_CHECK_0" if not fk_errors else f"FK_ERRORS:{len(fk_errors)}"})

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
