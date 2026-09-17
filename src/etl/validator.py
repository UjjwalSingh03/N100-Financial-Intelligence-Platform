"""Data-quality validation rules for Sprint 1 Day 03.

DQ-01 through DQ-16 are implemented against the actual supplied workbook
schemas. PK/FK integrity is CRITICAL; business-quality checks are WARNING.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

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


def _failures_from_mask(df: pd.DataFrame, mask: pd.Series, *, rule_id: str,
                        severity: str, table: str, column: str | None,
                        message: str) -> list[ValidationFailure]:
    failures: list[ValidationFailure] = []
    mask = mask.reindex(df.index, fill_value=False).fillna(False)
    for idx in df.index[mask]:
        value = df.loc[idx, column] if column and column in df.columns else None
        failures.append(ValidationFailure(rule_id, severity, table, int(idx) + 1, column, message, value))
    return failures


def validate_primary_key(df: pd.DataFrame, columns: str | Iterable[str], *,
                         table: str, rule_id: str = "DQ-01") -> list[ValidationFailure]:
    cols = [columns] if isinstance(columns, str) else list(columns)
    if not set(cols).issubset(df.columns):
        return []
    missing = df[cols].isna().any(axis=1)
    duplicate = df.duplicated(subset=cols, keep=False)
    return _failures_from_mask(df, missing | duplicate, rule_id=rule_id, severity=CRITICAL,
                               table=table, column=cols[0],
                               message=f"Primary key {cols} is missing or duplicated")


def validate_composite_year_key(df: pd.DataFrame, *, table: str,
                                company_col: str = "company_id",
                                year_col: str = "year") -> list[ValidationFailure]:
    return validate_primary_key(df, [company_col, year_col], table=table, rule_id="DQ-02")


def validate_foreign_key(child: pd.DataFrame, parent: pd.DataFrame, *,
                         child_column: str, parent_column: str, table: str,
                         rule_id: str = "DQ-03") -> list[ValidationFailure]:
    if child_column not in child.columns or parent_column not in parent.columns:
        return []
    valid = set(parent[parent_column].dropna())
    mask = child[child_column].notna() & ~child[child_column].isin(valid)
    return _failures_from_mask(child, mask, rule_id=rule_id, severity=CRITICAL,
                               table=table, column=child_column,
                               message=f"Foreign key does not exist in parent {parent_column}")


def validate_balance_sheet(df: pd.DataFrame, *, table: str = "balancesheet") -> list[ValidationFailure]:
    """DQ-04: total assets should reconcile to liabilities + equity within 1%."""
    assets = "total_assets" if "total_assets" in df.columns else None
    liabilities = "total_liabilities" if "total_liabilities" in df.columns else None
    if not all((assets, liabilities)):
        return []

    # The supplied workbook stores equity as equity_capital + reserves.
    if {"equity_capital", "reserves"}.issubset(df.columns):
        equity = pd.to_numeric(df["equity_capital"], errors="coerce") + pd.to_numeric(df["reserves"], errors="coerce")
    elif "total_equity" in df.columns:
        equity = pd.to_numeric(df["total_equity"], errors="coerce")
    elif "equity" in df.columns:
        equity = pd.to_numeric(df["equity"], errors="coerce")
    else:
        return []

    a = pd.to_numeric(df[assets], errors="coerce")
    l = pd.to_numeric(df[liabilities], errors="coerce")
    denominator = a.abs().replace(0, pd.NA)
    mask = a.notna() & l.notna() & equity.notna() & (((a - (l + equity)).abs() / denominator) > 0.01)
    return _failures_from_mask(df, mask, rule_id="DQ-04", severity=WARNING, table=table,
                               column=assets, message="Balance-sheet equation differs by more than 1%")


def validate_opm(df: pd.DataFrame, *, table: str = "profitandloss") -> list[ValidationFailure]:
    """DQ-05: reported OPM must agree with operating profit / sales."""
    required = {"sales", "operating_profit", "opm_percentage"}
    if not required.issubset(df.columns):
        return []
    sales = pd.to_numeric(df["sales"], errors="coerce")
    op = pd.to_numeric(df["operating_profit"], errors="coerce")
    reported = pd.to_numeric(df["opm_percentage"], errors="coerce")
    expected = op / sales.replace(0, pd.NA) * 100
    mask = expected.notna() & reported.notna() & ((expected - reported).abs() > 0.5)
    return _failures_from_mask(df, mask, rule_id="DQ-05", severity=WARNING, table=table,
                               column="opm_percentage", message="Reported OPM differs from operating profit / sales by more than 0.5 percentage points")


def validate_positive_sales(df: pd.DataFrame, *, table: str = "profitandloss") -> list[ValidationFailure]:
    """DQ-06: sales must be positive when present."""
    if "sales" not in df.columns:
        return []
    values = pd.to_numeric(df["sales"], errors="coerce")
    return _failures_from_mask(df, values.notna() & (values <= 0), rule_id="DQ-06", severity=WARNING,
                               table=table, column="sales", message="Sales must be positive")


def _numeric_check(df: pd.DataFrame, column: str, predicate: Callable[[pd.Series], pd.Series],
                   *, rule_id: str, table: str, message: str,
                   missing_is_failure: bool = False) -> list[ValidationFailure]:
    if column not in df.columns:
        return []
    values = pd.to_numeric(df[column], errors="coerce")
    mask = predicate(values)
    if missing_is_failure:
        mask = mask | values.isna()
    return _failures_from_mask(df, mask, rule_id=rule_id, severity=WARNING, table=table,
                               column=column, message=message)


def _text_check(df: pd.DataFrame, column: str, predicate: Callable[[pd.Series], pd.Series],
                *, rule_id: str, table: str, message: str) -> list[ValidationFailure]:
    if column not in df.columns:
        return []
    return _failures_from_mask(df, predicate(df[column]), rule_id=rule_id, severity=WARNING,
                               table=table, column=column, message=message)


def validate_rules(tables: dict[str, pd.DataFrame]) -> list[ValidationFailure]:
    """Run DQ-01 through DQ-16 using the supplied logical table mapping."""
    failures: list[ValidationFailure] = []

    # DQ-01: every physical id is unique and non-null.
    for table_name, df in tables.items():
        if "id" in df.columns:
            failures.extend(validate_primary_key(df, "id", table=table_name))

    # DQ-02: annual financial tables use (company_id, year) as the logical key.
    for table_name, df in tables.items():
        if {"company_id", "year"}.issubset(df.columns):
            failures.extend(validate_composite_year_key(df, table=table_name))

    # DQ-03: company references must exist in companies.id (the supplied data uses tickers as IDs).
    if "companies" in tables and "id" in tables["companies"].columns:
        parent = tables["companies"]
        for name, df in tables.items():
            if name != "companies" and "company_id" in df.columns:
                failures.extend(validate_foreign_key(df, parent, child_column="company_id",
                                                     parent_column="id", table=name))

    if "balancesheet" in tables:
        failures.extend(validate_balance_sheet(tables["balancesheet"]))
    if "profitandloss" in tables:
        failures.extend(validate_opm(tables["profitandloss"]))
        failures.extend(validate_positive_sales(tables["profitandloss"]))
        failures.extend(_numeric_check(tables["profitandloss"], "tax_percentage",
                                       lambda x: (x < 0) | (x > 100), rule_id="DQ-07",
                                       table="profitandloss", message="Tax percentage is outside 0% to 100%"))
        failures.extend(_numeric_check(tables["profitandloss"], "eps",
                                       lambda x: x.abs() > 1_000_000, rule_id="DQ-08",
                                       table="profitandloss", message="EPS is outside a sanity range"))
        failures.extend(_numeric_check(tables["profitandloss"], "dividend_payout",
                                       lambda x: x < 0, rule_id="DQ-09",
                                       table="profitandloss", message="Dividend payout cannot be negative"))
        failures.extend(_numeric_check(tables["profitandloss"], "dividend_payout",
                                       lambda x: (x < 0) | (x > 100), rule_id="DQ-10",
                                       table="profitandloss", message="Dividend payout is outside 0% to 100%"))
        failures.extend(_numeric_check(tables["profitandloss"], "eps",
                                       lambda x: x.isna(), rule_id="DQ-12",
                                       table="profitandloss", message="EPS is missing", missing_is_failure=True))
        failures.extend(_numeric_check(tables["profitandloss"], "net_profit",
                                       lambda x: x.isna(), rule_id="DQ-14",
                                       table="profitandloss", message="Net profit/PAT is missing", missing_is_failure=True))

    if "companies" in tables:
        failures.extend(_text_check(tables["companies"], "website",
                                    lambda x: x.isna() | ~x.astype(str).str.match(r"^(https?://|www\.)$|^(https?://|www\.)", na=False),
                                    rule_id="DQ-11", table="companies", message="Company URL is missing or not a web URL"))

    if "balancesheet" in tables:
        failures.extend(_numeric_check(tables["balancesheet"], "total_assets",
                                       lambda x: x <= 0, rule_id="DQ-13",
                                       table="balancesheet", message="Total assets must be positive"))

    if "stock_prices" in tables:
        failures.extend(_numeric_check(tables["stock_prices"], "close_price",
                                       lambda x: x <= 0, rule_id="DQ-15",
                                       table="stock_prices", message="Close price must be positive"))
        failures.extend(_text_check(tables["stock_prices"], "date",
                                    lambda x: pd.to_datetime(x, errors="coerce").isna(),
                                    rule_id="DQ-16", table="stock_prices", message="Price date is invalid or missing"))

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
