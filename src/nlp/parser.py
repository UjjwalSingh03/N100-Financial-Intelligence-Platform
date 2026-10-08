"""Day 29 — NLP analysis-text parser.

Parses the four text metrics from the source analysis workbook and
cross-validates 5-year sales/profit CAGR values against the Ratio Engine.

Run:
    python -m src.nlp.parser --analysis data/raw/analysis.xlsx --db db/nifty100.db

The source workbook is intentionally not required to be committed to Git.
When it is unavailable, the command fails clearly instead of fabricating
parsed output.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path
from typing import Iterable

import pandas as pd

TARGET_FIELDS = {
    "compounded_sales_growth": "compounded_sales_growth",
    "compounded_profit_growth": "compounded_profit_growth",
    "stock_price_cagr": "stock_price_cagr",
    "roe": "roe",
}

FIELD_ALIASES = {
    "compounded_sales_growth": {
        "compounded_sales_growth",
        "compounded_sales_growth_pct",
        "sales_growth",
        "sales_cagr",
    },
    "compounded_profit_growth": {
        "compounded_profit_growth",
        "compounded_profit_growth_pct",
        "profit_growth",
        "profit_cagr",
        "pat_growth",
        "pat_cagr",
    },
    "stock_price_cagr": {
        "stock_price_cagr",
        "stock_price_cagr_pct",
        "stock_cagr",
        "price_cagr",
    },
    "roe": {
        "roe",
        "roe_pct",
        "return_on_equity",
        "return_on_equity_pct",
    },
}

PATTERN = re.compile(r"(\d+)\s*Years?:?\s*([\d.]+)%", re.IGNORECASE)

CAGR_RATIO_MAP = {
    "compounded_sales_growth": "revenue_cagr_5yr",
    "compounded_profit_growth": "pat_cagr_5yr",
}

FAILURE_COLUMNS = [
    "company_id",
    "metric_type",
    "source_column",
    "source_text",
    "reason",
]

DIVERGENCE_COLUMNS = [
    "company_id",
    "metric_type",
    "period_years",
    "parsed_value_pct",
    "ratio_engine_value_pct",
    "divergence_pct",
    "review_flag",
]


def normalize_column(value: object) -> str:
    text = str(value).strip().lower()
    return re.sub(r"[^0-9a-z]+", "_", text).strip("_")


def find_source_column(columns: Iterable[object], metric_type: str) -> str | None:
    normalized = {normalize_column(c): str(c) for c in columns}
    for alias in FIELD_ALIASES[metric_type]:
        if alias in normalized:
            return normalized[alias]
    return None


def find_company_column(columns: Iterable[object]) -> str | None:
    normalized = {normalize_column(c): str(c) for c in columns}
    for candidate in ("company_id", "id", "ticker", "nse_code"):
        if candidate in normalized:
            return normalized[candidate]
    return None


def parse_text(value: object) -> list[tuple[int, float]]:
    if value is None or pd.isna(value):
        return []
    text = str(value).strip()
    return [(int(period), float(pct)) for period, pct in PATTERN.findall(text)]


def parse_analysis_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse target text fields from a wide analysis DataFrame."""
    company_col = find_company_column(df.columns)
    if company_col is None:
        raise ValueError("analysis source has no company_id/id/ticker/nse_code column")

    parsed: list[dict] = []
    failures: list[dict] = []

    for metric_type in TARGET_FIELDS.values():
        source_col = find_source_column(df.columns, metric_type)
        if source_col is None:
            failures.append({
                "company_id": "",
                "metric_type": metric_type,
                "source_column": "",
                "source_text": "",
                "reason": "target field not found in source workbook",
            })
            continue

        for _, row in df.iterrows():
            company_id = str(row.get(company_col, "")).strip()
            if not company_id or company_id.lower() == "nan":
                continue

            value = row.get(source_col)
            if value is None or pd.isna(value) or not str(value).strip():
                continue

            matches = parse_text(value)
            if not matches:
                failures.append({
                    "company_id": company_id,
                    "metric_type": metric_type,
                    "source_column": source_col,
                    "source_text": str(value),
                    "reason": "text does not match required regex",
                })
                continue

            for period_years, value_pct in matches:
                parsed.append({
                    "company_id": company_id,
                    "metric_type": metric_type,
                    "period_years": period_years,
                    "value_pct": value_pct,
                })

    parsed_df = pd.DataFrame(
        parsed,
        columns=["company_id", "metric_type", "period_years", "value_pct"],
    )
    failures_df = pd.DataFrame(failures, columns=FAILURE_COLUMNS)
    return parsed_df, failures_df


def read_analysis_workbook(path: Path) -> pd.DataFrame:
    """Read analysis.xlsx, tolerating the Bluestock banner row."""
    if not path.exists():
        raise FileNotFoundError(f"analysis workbook not found: {path}")

    candidates: list[pd.DataFrame] = []
    for header in (1, 0):
        frame = pd.read_excel(path, header=header)
        frame.columns = [normalize_column(c) for c in frame.columns]
        candidates.append(frame.dropna(how="all"))

    target_names = {
        alias for aliases in FIELD_ALIASES.values() for alias in aliases
    }
    company_names = {"company_id", "id", "ticker", "nse_code"}

    def score(frame: pd.DataFrame) -> int:
        cols = set(frame.columns)
        return len(cols & target_names) * 10 + len(cols & company_names) * 3

    return max(candidates, key=score)


def read_ratio_values(db_path: Path) -> pd.DataFrame:
    """Read the latest Ratio Engine CAGR values for each company."""
    if not db_path.exists():
        return pd.DataFrame(
            columns=["company_id", "year", "revenue_cagr_5yr", "pat_cagr_5yr"]
        )

    con = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(
            """
            SELECT company_id, year, revenue_cagr_5yr, pat_cagr_5yr
            FROM financial_ratios
            WHERE year = (
                SELECT MAX(r2.year)
                FROM financial_ratios r2
                WHERE r2.company_id = financial_ratios.company_id
            )
            """,
            con,
        )
    finally:
        con.close()


def cross_validate(
    parsed_df: pd.DataFrame,
    ratios_df: pd.DataFrame,
) -> pd.DataFrame:
    """Flag 5-year CAGR divergence greater than 5 percentage points."""
    if parsed_df.empty or ratios_df.empty:
        return pd.DataFrame(columns=DIVERGENCE_COLUMNS)

    rows: list[dict] = []
    ratios = ratios_df.copy()
    ratios["company_id"] = ratios["company_id"].astype(str)

    for _, item in parsed_df.iterrows():
        metric = str(item["metric_type"])
        ratio_col = CAGR_RATIO_MAP.get(metric)
        if ratio_col is None or int(item["period_years"]) != 5:
            continue

        matches = ratios[ratios["company_id"] == str(item["company_id"])]
        if matches.empty or pd.isna(matches.iloc[0].get(ratio_col)):
            continue

        parsed_value = float(item["value_pct"])
        engine_value = float(matches.iloc[0][ratio_col])
        divergence = abs(parsed_value - engine_value)

        if divergence > 5.0:
            rows.append({
                "company_id": str(item["company_id"]),
                "metric_type": metric,
                "period_years": int(item["period_years"]),
                "parsed_value_pct": parsed_value,
                "ratio_engine_value_pct": engine_value,
                "divergence_pct": divergence,
                "review_flag": "MANUAL_REVIEW",
            })

    return pd.DataFrame(rows, columns=DIVERGENCE_COLUMNS)


def run(
    analysis_path: Path,
    db_path: Path,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    output_dir.mkdir(parents=True, exist_ok=True)

    source = read_analysis_workbook(analysis_path)
    parsed, failures = parse_analysis_frame(source)
    ratios = read_ratio_values(db_path)
    divergences = cross_validate(parsed, ratios)

    parsed.to_csv(output_dir / "analysis_parsed.csv", index=False)
    failures.to_csv(output_dir / "parse_failures.csv", index=False)
    divergences.to_csv(output_dir / "cagr_divergences.csv", index=False)

    return parsed, failures, divergences


def main() -> int:
    parser = argparse.ArgumentParser(description="Day 29 analysis text parser")
    parser.add_argument("--analysis", type=Path, default=Path("data/raw/analysis.xlsx"))
    parser.add_argument("--db", type=Path, default=Path("db/nifty100.db"))
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    args = parser.parse_args()

    parsed, failures, divergences = run(
        args.analysis,
        args.db,
        args.output_dir,
    )

    print(f"parsed rows       : {len(parsed)}")
    print(f"parse failures    : {len(failures)}")
    print(f"manual review rows: {len(divergences)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
