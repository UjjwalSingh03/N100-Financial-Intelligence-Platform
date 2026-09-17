"""Data-quality validation rules for Sprint 1 Day 03.

The validator exposes DQ-01 through DQ-16 as deterministic checks.  Primary-key
and foreign-key integrity checks are CRITICAL; business-quality checks such as
OPM, balance-sheet balance, and positive sales are WARNING by default.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


CRITICAL = "CRITICAL"
WARNING = "WARNING"


@dataclass(frozen=True)
class ValidationFailure:
    rule_id: str
    severity: str
    table: str
    row: int | None
    column: str | None
    message: str
    value: Any = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _failures_from_mask(
    df: pd.DataFrame,
    mask: pd.Series,
    *,
    rule_id: str,
    severity: str,
    table: str,
    column: str | None,
    message: str,
) -> list[ValidationFailure]:
    failures: list[ValidationFailure] = []
    for idx in df.index[mask.fillna(False)]:
        value = df.loc[idx, column] if column and column in df.columns else None
        failures.append(
            ValidationFailure(rule_id, severity, table, int(idx) + 1, column, message, value)
        )
    return failures


def validate_primary_key(
    df: pd.DataFrame, columns: str | Iterable[str], *, table: str, rule_id: str = "DQ-01"
) -> list[ValidationFailure]:
    cols = [columns] if isinstance(columns, str) else list(columns)
    missing = df[cols].isna().any(axis=1)
    duplicate = df.duplicated(subset=cols, keep=False)
    mask = missing | duplicate
    return _failures_from_mask(
        df, mask, rule_id=rule_id, severity=CRITICAL, table=table,
        column=cols[0], message=f"Primary key {cols} is missing or duplicated",
    )


def validate_composite_year_key(
    df: pd.DataFrame, *, table: str, company_col: str = "company_id", year_col: str = "year"
) -> list[ValidationFailure]:
    return validate_primary_key(df, [company_col, year_col], table=table, rule_id="DQ-02")


def validate_foreign_key(
    child: pd.DataFrame, parent: pd.DataFrame, *, child_column: str, parent_column: str,
    table: str, rule_id: str = "DQ-03"
) -> list[ValidationFailure]:
    valid = set(parent[parent_column].dropna())
    mask = child[child_column].notna() & ~child[child_column].isin(valid)
    return _failures_from_mask(
        child, mask, rule_id=rule_id, severity=CRITICAL, table=table,
        column=child_column, message=f"Foreign key does not exist in parent {parent_column}",
    )


def validate_balance_sheet(df: pd.DataFrame, *, table: str = "balancesheet") -> list[ValidationFailure]:
    assets = next((c for c in ["total_assets", "assets"] if c in df.columns), None)
    liabilities = next((c for c in ["total_liabilities", "liabilities"] if c in df.columns), None)
    equity = next((c for c in ["total_equity", "equity"] if c in df.columns), None)
    if not all((assets, liabilities, equity)):
        return []
    a, l, e = [pd.to_numeric(df[c], errors="coerce") for c in (assets, liabilities, equity)]
    denominator = a.abs().replace(0, pd.NA)
    mask = ((a - (l + e)).abs() / denominator) > 0.01
    return _failures_from_mask(
        df, mask, rule_id="DQ-04", severity=WARNING, table=table, column=assets,
        message="Balance-sheet equation differs by more than 1%",
    )


def validate_opm(df: pd.DataFrame, *, table: str = "profitandloss") -> list[ValidationFailure]:
    sales_col = next((c for c in ["sales", "revenue", "total_sales"] if c in df.columns), None)
    op_col = next((c for c in ["operating_profit", "op_profit"] if c in df.columns), None)
    opm_col = next((c for c in ["opm", "operating_profit_margin"] if c in df.columns), None)
    if not all((sales_col, op_col, opm_col)):
        return []
    sales = pd.to_numeric(df[sales_col], errors="coerce")
    op = pd.to_numeric(df[op_col], errors="coerce")
    reported = pd.to_numeric(df[opm_col], errors="coerce")
    expected = op / sales.replace(0, pd.NA) * 100
    mask = expected.notna() & reported.notna() & ((expected - reported).abs() > 0.5)
    return _failures_from_mask(
        df, mask, rule_id="DQ-05", severity=WARNING, table=table, column=opm_col,
        message="Reported OPM differs from operating profit / sales by more than 0.5 percentage points",
    )


def validate_positive_sales(df: pd.DataFrame, *, table: str = "profitandloss") -> list[ValidationFailure]:
    sales_col = next((c for c in ["sales", "revenue", "total_sales"] if c in df.columns), None)
    if not sales_col:
        return []
    values = pd.to_numeric(df[sales_col], errors="coerce")
    return _failures_from_mask(
        df, values.notna() & (values <= 0), rule_id="DQ-06", severity=WARNING,
        table=table, column=sales_col, message="Sales must be positive",
    )


def _numeric_rule(df: pd.DataFrame, *, rule_id: str, table: str, columns: list[str],
                  predicate, message: str, severity: str = WARNING) -> list[ValidationFailure]:
    present = [c for c in columns if c in df.columns]
    if not present:
        return []
    failures: list[ValidationFailure] = []
    for col in present:
        values = pd.to_numeric(df[col], errors="coerce")
        mask = values.notna() & predicate(values)
        failures.extend(_failures_from_mask(df, mask, rule_id=rule_id, severity=severity,
                                             table=table, column=col, message=message))
    return failures


def validate_rules(tables: dict[str, pd.DataFrame]) -> list[ValidationFailure]:
    """Run DQ-01 through DQ-16 against a mapping of logical table names.

    Rules that depend on optional source columns simply produce no findings when
    those columns are absent, allowing the validator to work across source variants.
    """
    failures: list[ValidationFailure] = []

    # DQ-01 / DQ-02 / DQ-03
    for table_name, df in tables.items():
        if "id" in df.columns:
            failures.extend(validate_primary_key(df, "id", table=table_name))
        if {"company_id", "year"}.issubset(df.columns):
            failures.extend(validate_composite_year_key(df, table=table_name))

    if "companies" in tables:
        parent = tables["companies"]
        for name, df in tables.items():
            if name != "companies" and "company_id" in df.columns and "company_id" in parent.columns:
                failures.extend(validate_foreign_key(df, parent, child_column="company_id",
                                                     parent_column="company_id", table=name))

    # DQ-04 … DQ-06
    if "balancesheet" in tables:
        failures.extend(validate_balance_sheet(tables["balancesheet"]))
    if "profitandloss" in tables:
        failures.extend(validate_opm(tables["profitandloss"]))
        failures.extend(validate_positive_sales(tables["profitandloss"]))

    # DQ-07 … DQ-16: financial-domain sanity checks.
    checks = [
        ("DQ-07", "profitandloss", ["tax_rate", "tax_rate_pct"], lambda x: (x < -100) | (x > 100), "Tax rate is outside -100% to 100%"),
        ("DQ-08", "profitandloss", ["eps"], lambda x: x.abs() > 1000000, "EPS is outside a sanity range"),
        ("DQ-09", "profitandloss", ["dividend"], lambda x: x < 0, "Dividend cannot be negative"),
        ("DQ-10", "profitandloss", ["dividend_payout", "dividend_payout_ratio"], lambda x: (x < 0) | (x > 100), "Dividend payout ratio is outside 0% to 100%"),
        ("DQ-11", "companies", ["website", "url"], lambda x: ~x.astype(str).str.match(r"^(https?://|www\\.)", na=False), "Company URL is not a valid web-style URL"),
        ("DQ-12", "profitandloss", ["eps"], lambda x: x.isna(), "EPS is missing"),
        ("DQ-13", "balancesheet", ["total_assets", "assets"], lambda x: x <= 0, "Total assets must be positive"),
        ("DQ-14", "profitandloss", ["net_profit", "profit_after_tax", "pat"], lambda x: x.isna(), "Net profit/PAT is missing"),
        ("DQ-15", "stock_prices", ["close", "close_price", "price"], lambda x: x <= 0, "Stock price must be positive"),
        ("DQ-16", "stock_prices", ["date", "trade_date"], lambda x: pd.to_datetime(x, errors="coerce").isna(), "Price date is invalid or missing"),
    ]
    for rule_id, table, columns, predicate, message in checks:
        if table in tables:
            failures.extend(_numeric_rule(tables[table], rule_id=rule_id, table=table,
                                          columns=columns, predicate=predicate, message=message))

    return failures


def failures_to_frame(failures: Iterable[ValidationFailure]) -> pd.DataFrame:
    columns = ["rule_id", "severity", "table", "row", "column", "message", "value"]
    return pd.DataFrame([f.as_dict() for f in failures], columns=columns)


def write_validation_failures(failures: Iterable[ValidationFailure], output_path: str | Path) -> Path:
    """Write validation findings to CSV and return the output path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    failures_to_frame(failures).to_csv(path, index=False)
    return path
