"""Profitability ratio calculations for Sprint 2 Day 08.

The functions in this module are deliberately small and side-effect free so
that they can be reused by the SQLite ratio engine and unit-tested directly.
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
    """Calculate OPM and log when it differs from the source by >1 point.

    ``source_opm_percentage`` is the source workbook's OPM value.  The
    mismatch threshold is measured in percentage points, not relative percent.
    """
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
    """Calculate ROE using equity capital plus reserves.

    Negative or zero total equity is treated as an invalid denominator and
    returns None, as required by the Sprint 2 specification.
    """
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
    if profit is None or assets is None or assets == 0:
        return None
    return profit / assets * 100.0


def profitability_ratios(row: Mapping[str, object]) -> dict[str, float | None]:
    """Calculate all Day 08 profitability KPIs from a row-like mapping.

    Expected keys follow the Sprint 1 SQLite schema. ``ebit`` is accepted when
    supplied; otherwise ``operating_profit`` is used as the EBIT input.
    """
    ebit = row.get("ebit", row.get("operating_profit"))
    return {
        "net_profit_margin": net_profit_margin(row.get("net_profit"), row.get("sales")),
        "operating_profit_margin": operating_profit_margin(
            row.get("operating_profit"),
            row.get("sales"),
            row.get("opm_percentage"),
        ),
        "return_on_equity": return_on_equity(
            row.get("net_profit"),
            row.get("equity_capital"),
            row.get("reserves"),
        ),
        "return_on_capital_employed": return_on_capital_employed(
            ebit,
            row.get("equity_capital"),
            row.get("reserves"),
            row.get("borrowings"),
        ),
        "return_on_assets": return_on_assets(row.get("net_profit"), row.get("total_assets")),
    }


def roce_benchmark_type(broad_sector: str | None) -> str:
    """Return the benchmark category used for ROCE interpretation.

    Financial companies require a sector-relative benchmark; other sectors
    use the engine's absolute-threshold benchmark category.
    """
    return "sector_relative" if (broad_sector or "").strip().casefold() == "financials" else "absolute"
