"""Sprint 4 Day 26 — valuation analytics and valuation flagging.

The preferred source is market_cap.xlsx. When the workbook is not
available, the normalized SQLite tables are used so the dashboard-compatible
database can still generate the same valuation outputs.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path
from typing import Iterable

import pandas as pd

OUTPUT_COLUMNS = [
    "company_id",
    "company_name",
    "sector",
    "P/E",
    "P/B",
    "EV/EBITDA",
    "FCF_yield_pct",
    "5yr_median_PE",
    "PE_vs_sector_median_pct",
    "flag",
]


def _norm_col(value: object) -> str:
    return re.sub(r"[^0-9a-z]+", "_", str(value).strip().lower()).strip("_")


def _resolve_workbook(source: str | Path) -> Path:
    path = Path(source)
    if path.is_file():
        return path
    if not path.exists():
        raise FileNotFoundError(f"Valuation source does not exist: {path}")
    hits = sorted(path.glob("*market_cap*.xlsx")) + sorted(path.glob("*market_cap*.xls"))
    if not hits:
        raise FileNotFoundError(f"No market_cap workbook found in {path}")
    return hits[0]


def _prepare_market_cap_workbook(source: str | Path) -> pd.DataFrame:
    df = pd.read_excel(_resolve_workbook(source))
    df.columns = [_norm_col(c) for c in df.columns]

    aliases = {
        "company": "company_id",
        "companyid": "company_id",
        "ticker": "company_id",
        "symbol": "company_id",
        "market_cap_crore": "market_cap",
        "market_cap_cr": "market_cap",
        "market_cap": "market_cap",
        "enterprise_value_crore": "enterprise_value",
        "enterprise_value_cr": "enterprise_value",
        "enterprise_value": "enterprise_value",
        "pe": "pe_ratio",
        "p_e": "pe_ratio",
        "pe_ratio": "pe_ratio",
        "pb": "pb_ratio",
        "p_b": "pb_ratio",
        "pb_ratio": "pb_ratio",
        "ev_ebitda": "ev_ebitda",
        "ev_ebitda_ratio": "ev_ebitda",
        "fcf": "free_cash_flow_cr",
        "free_cash_flow": "free_cash_flow_cr",
        "free_cash_flow_cr": "free_cash_flow_cr",
    }
    df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})

    if "company_id" not in df.columns:
        raise ValueError("market_cap.xlsx must contain a company/ticker identifier")

    for col in (
        "year", "market_cap", "enterprise_value", "pe_ratio", "pb_ratio",
        "ev_ebitda", "free_cash_flow_cr",
    ):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "year" not in df.columns:
        df["year"] = pd.NA

    return df


def _load_db_frame(db_path: str | Path) -> pd.DataFrame:
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")

    con = sqlite3.connect(path)
    try:
        sql = """
        SELECT
            c.id AS company_id,
            c.company_name,
            COALESCE(NULLIF(s.sector, ''), 'Unknown') AS sector,
            m.year,
            m.market_cap,
            m.enterprise_value,
            p.net_profit,
            p.operating_profit,
            p.depreciation,
            b.equity_capital,
            b.reserves,
            fr.free_cash_flow_cr
        FROM companies c
        LEFT JOIN sectors s ON s.company_id = c.id
        LEFT JOIN market_cap m ON m.company_id = c.id
        LEFT JOIN profitandloss p
          ON p.company_id = c.id AND p.year = m.year
        LEFT JOIN balancesheet b
          ON b.company_id = c.id AND b.year = m.year
        LEFT JOIN financial_ratios fr
          ON fr.company_id = c.id AND fr.year = m.year
        """
        return pd.read_sql_query(sql, con)
    finally:
        con.close()


def _calculate_from_db(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    numeric = [
        "market_cap", "enterprise_value", "net_profit", "operating_profit",
        "depreciation", "equity_capital", "reserves", "free_cash_flow_cr",
    ]
    for col in numeric:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    frame["P/E"] = frame["market_cap"].div(
        frame["net_profit"].where(frame["net_profit"] > 0)
    )
    book_value = frame["equity_capital"].fillna(0) + frame["reserves"].fillna(0)
    frame["P/B"] = frame["market_cap"].div(book_value.where(book_value > 0))

    ebitda = frame["operating_profit"].fillna(0) + frame["depreciation"].fillna(0)
    frame["EV/EBITDA"] = frame["enterprise_value"].div(ebitda.where(ebitda > 0))
    frame["FCF_yield_pct"] = frame["free_cash_flow_cr"].div(
        frame["market_cap"].where(frame["market_cap"] > 0)
    ).mul(100)
    return frame


def _calculate_from_workbook(workbook: pd.DataFrame, db_path: str | Path) -> pd.DataFrame:
    """Enrich market_cap.xlsx with company, sector and FCF information."""
    con = sqlite3.connect(db_path)
    try:
        companies = pd.read_sql_query(
            "SELECT id AS company_id, company_name FROM companies", con
        )
        sectors = pd.read_sql_query(
            "SELECT company_id, sector FROM sectors", con
        )
        ratios = pd.read_sql_query(
            "SELECT company_id, year, free_cash_flow_cr FROM financial_ratios", con
        )
        pnl = pd.read_sql_query(
            "SELECT company_id, year, net_profit, operating_profit, depreciation FROM profitandloss",
            con,
        )
        bs = pd.read_sql_query(
            "SELECT company_id, year, equity_capital, reserves FROM balancesheet", con
        )
    finally:
        con.close()

    df = workbook.copy()
    df["company_id"] = df["company_id"].astype(str).str.strip()
    for lookup in (companies, sectors):
        lookup["company_id"] = lookup["company_id"].astype(str).str.strip()

    df = df.merge(companies, on="company_id", how="left")
    df = df.merge(sectors.drop_duplicates("company_id"), on="company_id", how="left")

    if "year" in df.columns:
        df = df.merge(
            pnl.drop_duplicates(["company_id", "year"]),
            on=["company_id", "year"],
            how="left",
            suffixes=("", "_pnl"),
        )
        df = df.merge(
            bs.drop_duplicates(["company_id", "year"]),
            on=["company_id", "year"],
            how="left",
        )
        df = df.merge(
            ratios.drop_duplicates(["company_id", "year"]),
            on=["company_id", "year"],
            how="left",
        )

    for col in (
        "market_cap", "enterprise_value", "net_profit", "operating_profit",
        "depreciation", "equity_capital", "reserves", "free_cash_flow_cr",
        "pe_ratio", "pb_ratio", "ev_ebitda",
    ):
        if col not in df.columns:
            df[col] = pd.NA
        df[col] = pd.to_numeric(df[col], errors="coerce")

    calculated_pe = df["market_cap"].div(
        df["net_profit"].where(df["net_profit"] > 0)
    )
    calculated_pb = df["market_cap"].div(
        (df["equity_capital"].fillna(0) + df["reserves"].fillna(0)).where(
            (df["equity_capital"].fillna(0) + df["reserves"].fillna(0)) > 0
        )
    )
    ebitda = df["operating_profit"].fillna(0) + df["depreciation"].fillna(0)
    calculated_ev_ebitda = df["enterprise_value"].div(ebitda.where(ebitda > 0))
    calculated_fcf_yield = df["free_cash_flow_cr"].div(
        df["market_cap"].where(df["market_cap"] > 0)
    ).mul(100)

    df["P/E"] = df["pe_ratio"].fillna(calculated_pe)
    df["P/B"] = df["pb_ratio"].fillna(calculated_pb)
    df["EV/EBITDA"] = df["ev_ebitda"].fillna(calculated_ev_ebitda)
    df["FCF_yield_pct"] = calculated_fcf_yield
    return df


def _latest_per_company(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["year"] = pd.to_numeric(frame["year"], errors="coerce")
    frame = frame.sort_values(["company_id", "year"])
    return frame.groupby("company_id", as_index=False).tail(1).reset_index(drop=True)


def _add_valuation_flags(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["sector"] = frame["sector"].fillna("Unknown").replace("", "Unknown")
    frame["P/E"] = pd.to_numeric(frame["P/E"], errors="coerce")

    sector_medians = (
        frame.loc[frame["P/E"].gt(0)]
        .groupby("sector")["P/E"]
        .median()
        .rename("sector_median_pe")
    )
    frame = frame.merge(sector_medians, left_on="sector", right_index=True, how="left")

    history = frame[["company_id", "year", "P/E"]].copy()
    history = history.sort_values(["company_id", "year"])
    medians = (
        history.groupby("company_id")["P/E"]
        .apply(lambda s: s.dropna().loc[s.dropna().gt(0)].tail(5).median())
        .rename("5yr_median_PE")
    )
    frame = frame.merge(medians, left_on="company_id", right_index=True, how="left")

    frame["PE_vs_sector_median_pct"] = (
        frame["P/E"].div(frame["sector_median_pe"]).sub(1).mul(100)
    )

    def flag(row: pd.Series) -> str:
        pe = row["P/E"]
        median = row["sector_median_pe"]
        if pd.isna(pe) or pd.isna(median) or median <= 0:
            return "Fair"
        if pe > median * 1.5:
            return "Caution"
        if pe < median * 0.7:
            return "Discount"
        return "Fair"

    frame["flag"] = frame.apply(flag, axis=1)
    return frame


def build_valuation_summary(
    db_path: str | Path = "db/nifty100.db",
    market_cap_source: str | Path | None = "data/raw",
) -> pd.DataFrame:
    """Build the latest-year valuation summary for all available companies."""
    source = Path(market_cap_source) if market_cap_source else None
    if source is not None and source.exists():
        try:
            workbook = _prepare_market_cap_workbook(source)
            frame = _calculate_from_workbook(workbook, db_path)
        except (FileNotFoundError, ValueError):
            frame = _calculate_from_db(_load_db_frame(db_path))
    else:
        frame = _calculate_from_db(_load_db_frame(db_path))

    if frame.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    frame = frame.copy()
    frame["company_id"] = frame["company_id"].astype(str)
    frame["company_name"] = frame.get("company_name", frame["company_id"])
    frame["sector"] = frame.get("sector", "Unknown").fillna("Unknown")

    flagged = _add_valuation_flags(frame)
    latest = _latest_per_company(flagged)

    result = latest.reindex(columns=OUTPUT_COLUMNS).copy()
    result = result.sort_values(["flag", "company_name"], na_position="last").reset_index(drop=True)
    return result


def write_valuation_outputs(
    db_path: str | Path = "db/nifty100.db",
    market_cap_source: str | Path = "data/raw",
    output_dir: str | Path = "output",
) -> tuple[pd.DataFrame, Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    summary = build_valuation_summary(db_path, market_cap_source)
    summary_path = output / "valuation_summary.xlsx"
    flags_path = output / "valuation_flags.csv"

    summary.to_excel(summary_path, index=False)
    summary.loc[summary["flag"].isin(["Caution", "Discount"])].to_csv(
        flags_path, index=False
    )
    return summary, summary_path, flags_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Day 26 valuation outputs")
    parser.add_argument("--db", default="db/nifty100.db")
    parser.add_argument("--market-cap", default="data/raw")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    summary, summary_path, flags_path = write_valuation_outputs(
        args.db, args.market_cap, args.output_dir
    )
    print(f"Valuation companies: {len(summary)}")
    print(f"Caution: {(summary['flag'] == 'Caution').sum()}")
    print(f"Discount: {(summary['flag'] == 'Discount').sum()}")
    print(f"Fair: {(summary['flag'] == 'Fair').sum()}")
    print(f"Summary: {summary_path}")
    print(f"Flags: {flags_path}")


if __name__ == "__main__":
    main()
