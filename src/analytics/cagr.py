"""CAGR calculations for Sprint 2 Day 10.

Supports Revenue, PAT, and EPS growth across 3-, 5-, and 10-year windows,
including explicit flags for sign changes, zero bases, and insufficient data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class CAGRResult:
    """CAGR value plus the required edge-case flag."""

    value: float | None
    flag: str | None = None


VALID_FLAGS = {
    None,
    "DECLINE_TO_LOSS",
    "TURNAROUND",
    "BOTH_NEGATIVE",
    "ZERO_BASE",
    "INSUFFICIENT",
}


def calculate_cagr(start: float | None, end: float | None, n_years: int) -> CAGRResult:
    """Calculate CAGR and classify all six required cases."""
    if n_years <= 0:
        raise ValueError("n_years must be positive")
    if start is None or end is None:
        return CAGRResult(None, "INSUFFICIENT")

    start = float(start)
    end = float(end)

    if start == 0:
        return CAGRResult(None, "ZERO_BASE")
    if start > 0 and end > 0:
        return CAGRResult(((end / start) ** (1 / n_years) - 1) * 100, None)
    if start > 0 and end < 0:
        return CAGRResult(None, "DECLINE_TO_LOSS")
    if start < 0 and end > 0:
        return CAGRResult(None, "TURNAROUND")
    if start < 0 and end < 0:
        return CAGRResult(None, "BOTH_NEGATIVE")
    # End == 0 cannot produce a meaningful CAGR under the requested rules.
    return CAGRResult(None, "DECLINE_TO_LOSS")


def _ordered_values(values: Sequence[object]) -> list[float | None]:
    """Convert a chronological value sequence to numeric values."""
    result: list[float | None] = []
    for value in values:
        if value is None or isinstance(value, bool):
            result.append(None)
            continue
        try:
            result.append(float(value))
        except (TypeError, ValueError):
            result.append(None)
    return result


def cagr_for_window(values: Sequence[object], n_years: int) -> CAGRResult:
    """Calculate CAGR from a chronological series for a requested year window.

    The sequence must contain at least n_years + 1 observations to span n_years.
    The first and last observations define the CAGR endpoints.
    """
    if len(values) < n_years + 1:
        return CAGRResult(None, "INSUFFICIENT")

    numeric = _ordered_values(values)
    return calculate_cagr(numeric[0], numeric[n_years], n_years)


def growth_metrics(values: Sequence[object]) -> dict[str, CAGRResult]:
    """Return 3-, 5-, and 10-year CAGR results for one metric series."""
    return {
        "3yr": cagr_for_window(values, 3),
        "5yr": cagr_for_window(values, 5),
        "10yr": cagr_for_window(values, 10),
    }


def growth_metrics_all(
    revenue: Sequence[object],
    pat: Sequence[object],
    eps: Sequence[object],
) -> dict[str, CAGRResult]:
    """Return Revenue, PAT, and EPS CAGR results for all required windows."""
    return {
        **{f"revenue_cagr_{k}": v for k, v in growth_metrics(revenue).items()},
        **{f"pat_cagr_{k}": v for k, v in growth_metrics(pat).items()},
        **{f"eps_cagr_{k}": v for k, v in growth_metrics(eps).items()},
    }


def cagr_columns(
    revenue: Sequence[object],
    pat: Sequence[object],
    eps: Sequence[object],
) -> dict[str, float | str | None]:
    """Flatten values and flags into database-ready columns."""
    results = growth_metrics_all(revenue, pat, eps)
    output: dict[str, float | str | None] = {}
    for name, result in results.items():
        output[name] = result.value
        output[f"{name}_flag"] = result.flag
    return output
