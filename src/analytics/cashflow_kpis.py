"""Sprint 5 Day 31 — company-level cash-flow intelligence and distress alerts.

Run:
    python -m src.analytics.cashflow_kpis --db db/nifty100.db --output-dir output
"""
from __future__ import annotations

import argparse
import math
import sqlite3
from pathlib import Path

import pandas as pd

from .cash_flow import (
    capital_allocation_pattern, capex_intensity, capex_intensity_label,
    cash_flow_kpis, cash_sign, cfo_quality_label, cfo_quality_score,
    fcf_conversion_rate, free_cash_flow,
)

OUTPUT_COLUMNS = [
    "company_id", "sector", "cfo_quality_score", "cfo_quality_label",
    "capex_intensity_pct", "capex_label", "fcf_cagr_5yr",
    "fcf_conversion_pct", "distress_flag", "deleveraging_flag",
    "capital_allocation_label",
]
ALERT_COLUMNS = ["company_id", "sector", "cfo_value", "cff_value", "latest_net_profit"]


def _number(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _read_table(con: sqlite3.Connection, table: str) -> pd.DataFrame:
    exists = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?", (table,)
    ).fetchone()
    return pd.read_sql_query(f'SELECT * FROM "{table}"', con) if exists else pd.DataFrame()


def _find_col(df: pd.DataFrame, *names: str) -> str | None:
    cols = {str(c).casefold(): str(c) for c in df.columns}
    return next((cols[name.casefold()] for name in names if name.casefold() in cols), None)


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["company_id", "year"])
    id_col, year_col = _find_col(df, "company_id", "id", "ticker"), _find_col(df, "year", "financial_year")
    if not id_col or not year_col:
        return pd.DataFrame(columns=["company_id", "year"])
    result = df.rename(columns={id_col: "company_id", year_col: "year"}).copy()
    result["company_id"] = result["company_id"].astype(str)
    result["year"] = pd.to_numeric(result["year"], errors="coerce")
    result = result.dropna(subset=["year"])
    result["year"] = result["year"].astype(int)
    return result


def _fcf_cagr(series: pd.Series, years: int = 5) -> float | None:
    """Calculate CAGR only where positive start/end FCF and a full period exist."""
    values = series.dropna().sort_index()
    if values.empty:
        return None
    end_year, end_value = int(values.index[-1]), _number(values.iloc[-1])
    if end_value is None or end_value <= 0:
        return None
    eligible = [(int(y), _number(v)) for y, v in values.items() if int(y) <= end_year - years]
    eligible = [(y, v) for y, v in eligible if v is not None and v > 0]
    if not eligible:
        return None
    start_year, start_value = eligible[-1]
    elapsed = end_year - start_year
    return ((end_value / start_value) ** (1 / elapsed) - 1) * 100 if elapsed >= years else None


def calculate_cashflow_intelligence(db_path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return one intelligence row per company and a distress-alert dataframe."""
    with sqlite3.connect(str(db_path)) as con:
        companies = _read_table(con, "companies")
        pl = _normalize(_read_table(con, "profitandloss"))
        cf = _normalize(_read_table(con, "cashflow"))
        bs = _normalize(_read_table(con, "balancesheet"))
        ratios = _normalize(_read_table(con, "financial_ratios"))

    if companies.empty:
        raise ValueError("Database must contain a non-empty companies table.")
    id_col = _find_col(companies, "id", "company_id", "ticker")
    sector_col = _find_col(companies, "sector", "broad_sector")
    if not id_col:
        raise ValueError("companies table requires id or company_id.")
    companies = companies.copy()
    companies["company_id"] = companies[id_col].astype(str)
    companies["sector"] = companies[sector_col].fillna("Unknown").astype(str) if sector_col else "Unknown"

    sales_col = _find_col(pl, "sales", "revenue", "total_revenue")
    pat_col = _find_col(pl, "net_profit", "pat", "profit_after_tax")
    cfo_col = _find_col(cf, "cash_from_operating_activity", "operating_activity", "cash_from_operations_cr", "cfo")
    cfi_col = _find_col(cf, "cash_from_investing_activity", "investing_activity", "cfi")
    cff_col = _find_col(cf, "cash_from_financing_activity", "financing_activity", "cff")
    debt_col = _find_col(bs, "borrowings", "total_debt_cr", "total_debt")
    fcf_col = _find_col(ratios, "free_cash_flow_cr", "free_cash_flow", "fcf")
    cfo_ratio_col = _find_col(ratios, "cash_from_operations_cr", "cash_from_operating_activity")

    output_rows: list[dict] = []
    alert_rows: list[dict] = []
    for _, company in companies.iterrows():
        company_id, sector = company["company_id"], company["sector"]
        plc = pl[pl.company_id == company_id].sort_values("year").drop_duplicates("year", keep="last")
        cfc = cf[cf.company_id == company_id].sort_values("year").drop_duplicates("year", keep="last")
        bsc = bs[bs.company_id == company_id].sort_values("year").drop_duplicates("year", keep="last")
        rc = ratios[ratios.company_id == company_id].sort_values("year").drop_duplicates("year", keep="last")

        pat_by_year = {int(r.year): _number(r.get(pat_col)) for _, r in plc.iterrows()} if pat_col else {}
        cfo_by_year = {int(r.year): _number(r.get(cfo_col)) for _, r in cfc.iterrows()} if cfo_col else {}
        if not cfo_by_year and cfo_ratio_col:
            cfo_by_year = {int(r.year): _number(r.get(cfo_ratio_col)) for _, r in rc.iterrows()}
        common_years = sorted(set(pat_by_year) & set(cfo_by_year))[-5:]
        cfo_ratios = [{"pat": pat_by_year[y], "cfo": cfo_by_year[y]} for y in common_years]
        score = cfo_quality_score(cfo_ratios)

        latest_pl = plc.iloc[-1] if not plc.empty else pd.Series(dtype=object)
        latest_cf = cfc.iloc[-1] if not cfc.empty else pd.Series(dtype=object)
        latest_year = int(latest_cf["year"]) if not cfc.empty else (int(latest_pl["year"]) if not plc.empty else None)
        sales = _number(latest_pl.get(sales_col)) if sales_col else None
        latest_pat = _number(latest_pl.get(pat_col)) if pat_col else None
        cfo = _number(latest_cf.get(cfo_col)) if cfo_col else None
        cfi = _number(latest_cf.get(cfi_col)) if cfi_col else None
        cff = _number(latest_cf.get(cff_col)) if cff_col else None

        intensity = capex_intensity(cfi, sales)
        fcf_by_year: dict[int, float] = {}
        if fcf_col:
            fcf_by_year = {int(r.year): v for _, r in rc.iterrows() if (v := _number(r.get(fcf_col))) is not None}
        if not fcf_by_year and cfo_col and cfi_col:
            for _, r in cfc.iterrows():
                op, inv = _number(r.get(cfo_col)), _number(r.get(cfi_col))
                if op is not None and inv is not None:
                    fcf_by_year[int(r.year)] = op + inv
        fcf_series = pd.Series(fcf_by_year, dtype=float).sort_index()
        fcf_cagr = _fcf_cagr(fcf_series, 5)
        latest_fcf = fcf_by_year.get(latest_year) if latest_year is not None else None
        # Conversion is defined as FCF / PAT; percentage is undefined for zero/missing PAT.
        conversion = latest_fcf / latest_pat * 100 if latest_fcf is not None and latest_pat not in (None, 0) else None

        distress = cfo is not None and cff is not None and cfo < 0 and cff > 0
        debt_series = [(int(r.year), _number(r.get(debt_col))) for _, r in bsc.iterrows()] if debt_col else []
        debt_series = sorted((y, d) for y, d in debt_series if d is not None)
        deleveraging = bool(cff is not None and cff < 0 and len(debt_series) >= 2 and debt_series[-1][1] < debt_series[-2][1])
        output_rows.append({
            "company_id": company_id, "sector": sector,
            "cfo_quality_score": score, "cfo_quality_label": cfo_quality_label(score) or "Insufficient Data",
            "capex_intensity_pct": intensity, "capex_label": capex_intensity_label(intensity) or "Insufficient Data",
            "fcf_cagr_5yr": fcf_cagr, "fcf_conversion_pct": conversion,
            "distress_flag": bool(distress), "deleveraging_flag": deleveraging,
            "capital_allocation_label": capital_allocation_pattern(cfo, cfi, cff, score),
        })
        if distress:
            alert_rows.append({
                "company_id": company_id, "sector": sector, "cfo_value": cfo,
                "cff_value": cff, "latest_net_profit": latest_pat,
            })

    return pd.DataFrame(output_rows, columns=OUTPUT_COLUMNS), pd.DataFrame(alert_rows, columns=ALERT_COLUMNS)


def generate(db_path: str | Path = "db/nifty100.db", output_dir: str | Path = "output") -> tuple[Path, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    intelligence, alerts = calculate_cashflow_intelligence(db_path)
    workbook = output_dir / "cashflow_intelligence.xlsx"
    alert_csv = output_dir / "distress_alerts.csv"
    intelligence.to_excel(workbook, index=False, sheet_name="Cash Flow Intelligence")
    alerts.to_csv(alert_csv, index=False)
    return workbook, alert_csv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="db/nifty100.db")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()
    workbook, alerts = generate(args.db, args.output_dir)
    print(f"Generated {workbook} and {alerts}")


if __name__ == "__main__":
    main()


__all__ = [
    "capital_allocation_pattern", "capex_intensity", "capex_intensity_label",
    "calculate_cashflow_intelligence", "cash_flow_kpis", "cash_sign",
    "cfo_quality_label", "cfo_quality_score", "fcf_conversion_rate",
    "free_cash_flow", "generate",
]
