"""Financial ratio calculations for Sprint 2 Days 08-09.

The functions are side-effect free so they can be reused by the ratio engine
and unit-tested independently.
"""

from __future__ import annotations

import logging
from typing import Mapping

logger = logging.getLogger(__name__)

Number = int | float


def _number(value: object) -> float | None:
    """Return a finite numeric value, or None for missing/non-numeric input."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def net_profit_margin(net_profit: Number | None, sales: Number | None) -> float | None:
    """Calculate Net Profit Margin as net profit / sales * 100."""
    profit = _number(net_profit)
    revenue = _number(sales)
    if profit is None or revenue is None or revenue == 0:
        return None
    return profit / revenue * 100.0


def operating_profit_margin(
    operating_profit: Number | None,
    sales: Number | None,
    source_opm_percentage: Number | None = None,
    *,
    mismatch_threshold: float = 1.0,
) -> float | None:
    """Calculate OPM and log when it differs from the source by >1 point."""
    op = _number(operating_profit)
    revenue = _number(sales)
    source = _number(source_opm_percentage)
    if op is None or revenue is None or revenue == 0:
        return None

    calculated = op / revenue * 100.0
    if source is not None and abs(calculated - source) > mismatch_threshold:
        logger.warning(
            "OPM mismatch: calculated=%.4f%% source=%.4f%% difference=%.4f points",
            calculated,
            source,
            abs(calculated - source),
        )
    return calculated


def return_on_equity(
    net_profit: Number | None,
    equity_capital: Number | None,
    reserves: Number | None,
) -> float | None:
    """Calculate ROE using equity capital plus reserves."""
    profit = _number(net_profit)
    equity = _number(equity_capital)
    reserve_value = _number(reserves)
    if profit is None or equity is None or reserve_value is None:
        return None

    total_equity = equity + reserve_value
    if total_equity <= 0:
        return None
    return profit / total_equity * 100.0


def return_on_capital_employed(
    ebit: Number | None,
    equity_capital: Number | None,
    reserves: Number | None,
    borrowings: Number | None,
) -> float | None:
    """Calculate ROCE as EBIT / (equity + reserves + borrowings) * 100."""
    earnings = _number(ebit)
    equity = _number(equity_capital)
    reserve_value = _number(reserves)
    debt = _number(borrowings)
    if any(value is None for value in (earnings, equity, reserve_value, debt)):
        return None

    capital = equity + reserve_value + debt
    if capital <= 0:
        return None
    return earnings / capital * 100.0


def return_on_assets(net_profit: Number | None, total_assets: Number | None) -> float | None:
    """Calculate ROA as net profit / total assets * 100."""
    profit = _number(net_profit)
    assets = _number(total_assets)
    if profit is None or assets == 0:
        return None
    return profit / assets * 100.0 if assets is not None else None


def debt_to_equity(
    borrowings: Number | None,
    equity_capital: Number | None,
    reserves: Number | None,
) -> float | None:
    """Calculate D/E as borrowings / (equity capital + reserves).

    Debt-free companies explicitly return 0. Negative or zero equity is treated
    as an invalid denominator.
    """
    debt = _number(borrowings)
    equity = _number(equity_capital)
    reserve_value = _number(reserves)
    if debt is None or equity is None or reserve_value is None:
        return None
    if debt == 0:
        return 0.0

    total_equity = equity + reserve_value
    if total_equity <= 0:
        return None
    return debt / total_equity


def high_leverage_flag(debt_to_equity_value: Number | None, broad_sector: str | None) -> bool:
    """Flag D/E above 5 outside the Financials sector."""
    debt_equity = _number(debt_to_equity_value)
    is_financials = (broad_sector or "").strip().casefold() == "financials"
    return bool(debt_equity is not None and debt_equity > 5 and not is_financials)


def interest_coverage_ratio(
    operating_profit: Number | None,
    other_income: Number | None,
    interest: Number | None,
) -> float | None:
    """Calculate ICR as (operating profit + other income) / interest."""
    operating = _number(operating_profit)
    other = _number(other_income)
    interest_expense = _number(interest)
    if operating is None or other is None or interest_expense is None:
        return None
    if interest_expense == 0:
        return None
    return (operating + other) / interest_expense


def icr_label(icr: Number | None) -> str | None:
    """Return 'Debt Free' when ICR is None; otherwise no display label."""
    return "Debt Free" if icr is None else None


def icr_warning_flag(icr: Number | None) -> bool:
    """Flag ICR below 1.5 as a potential interest-coverage risk."""
    coverage = _number(icr)
    return bool(coverage is not None and coverage < 1.5)


def net_debt(borrowings: Number | None, investments: Number | None) -> float | None:
    """Calculate net debt as borrowings minus investments."""
    debt = _number(borrowings)
    liquid_assets = _number(investments)
    if debt is None or liquid_assets is None:
        return None
    return debt - liquid_assets


def asset_turnover(sales: Number | None, total_assets: Number | None) -> float | None:
    """Calculate Asset Turnover as sales / total assets."""
    revenue = _number(sales)
    assets = _number(total_assets)
    if revenue is None or assets is None or assets == 0:
        return None
    return revenue / assets


def profitability_ratios(row: Mapping[str, object]) -> dict[str, float | None]:
    """Calculate all Day 08 profitability KPIs from a row-like mapping."""
    ebit = row.get("ebit", row.get("operating_profit"))
    return {
        "net_profit_margin": net_profit_margin(row.get("net_profit"), row.get("sales")),
        "operating_profit_margin": operating_profit_margin(
            row.get("operating_profit"),
            row.get("sales"),
            row.get("opm_percentage"),
        ),
        "return_on_equity": return_on_equity(
            row.get("net_profit"), row.get("equity_capital"), row.get("reserves")
        ),
        "return_on_capital_employed": return_on_capital_employed(
            ebit, row.get("equity_capital"), row.get("reserves"), row.get("borrowings")
        ),
        "return_on_assets": return_on_assets(row.get("net_profit"), row.get("total_assets")),
    }


def leverage_efficiency_ratios(row: Mapping[str, object]) -> dict[str, object]:
    """Calculate Day 09 leverage and efficiency KPIs and display flags."""
    debt_equity = debt_to_equity(
        row.get("borrowings"), row.get("equity_capital"), row.get("reserves")
    )
    coverage = interest_coverage_ratio(
        row.get("operating_profit"),
        row.get("other_income"),
        row.get("interest"),
    )
    return {
        "debt_to_equity": debt_equity,
        "high_leverage_flag": high_leverage_flag(debt_equity, row.get("broad_sector")),
        "interest_coverage_ratio": coverage,
        "icr_label": icr_label(coverage),
        "icr_warning_flag": icr_warning_flag(coverage),
        "net_debt": net_debt(row.get("borrowings"), row.get("investments")),
        "asset_turnover": asset_turnover(row.get("sales"), row.get("total_assets")),
    }


def roce_benchmark_type(broad_sector: str | None) -> str:
    """Return the benchmark category used for ROCE interpretation."""
    return (
        "sector_relative"
        if (broad_sector or "").strip().casefold() == "financials"
        else "absolute"
    )
