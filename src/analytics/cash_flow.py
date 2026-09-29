"""Cash-flow KPIs and capital-allocation classification for Sprint 2 Day 11."""

from __future__ import annotations

from typing import Mapping, Sequence

Number = int | float


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def free_cash_flow(
    operating_activity: Number | None,
    investing_activity: Number | None,
) -> float | None:
    """FCF = operating cash flow + investing cash flow; negative values are valid."""
    cfo = _number(operating_activity)
    cfi = _number(investing_activity)
    if cfo is None or cfi is None:
        return None
    return cfo + cfi


def cfo_quality_score(cfo_pat_ratios: Sequence[object]) -> float | None:
    """Return the average CFO/PAT ratio over the supplied five-year window.

    Missing values are ignored. A PAT value of zero is excluded because the
    requested ratio is undefined. None is returned when no valid ratio exists.
    """
    ratios: list[float] = []
    for item in cfo_pat_ratios:
        if isinstance(item, Mapping):
            cfo = _number(item.get("cfo"))
            pat = _number(item.get("pat"))
            if cfo is None or pat is None or pat == 0:
                continue
            ratios.append(cfo / pat)
        else:
            value = _number(item)
            if value is not None:
                ratios.append(value)
    return sum(ratios) / len(ratios) if ratios else None


def cfo_quality_label(score: Number | None) -> str | None:
    """Classify the CFO quality score."""
    value = _number(score)
    if value is None:
        return None
    if value > 1.0:
        return "High Quality"
    if value >= 0.5:
        return "Moderate"
    return "Accrual Risk"


def capex_intensity(
    investing_activity: Number | None,
    sales: Number | None,
) -> float | None:
    """CapEx intensity = abs(CFI) / sales * 100."""
    cfi = _number(investing_activity)
    revenue = _number(sales)
    if cfi is None or revenue is None or revenue == 0:
        return None
    return abs(cfi) / revenue * 100.0


def capex_intensity_label(intensity: Number | None) -> str | None:
    """Classify CapEx intensity."""
    value = _number(intensity)
    if value is None:
        return None
    if value < 3:
        return "Asset Light"
    if value <= 8:
        return "Moderate"
    return "Capital Intensive"


def fcf_conversion_rate(
    fcf: Number | None,
    operating_profit: Number | None,
) -> float | None:
    """FCF conversion = FCF / operating profit * 100."""
    cash = _number(fcf)
    profit = _number(operating_profit)
    if cash is None or profit is None or profit == 0:
        return None
    return cash / profit * 100.0


def cash_sign(value: Number | None) -> str:
    """Return the sign used by the capital-allocation classifier."""
    number = _number(value)
    if number is None or number == 0:
        return "0"
    return "+" if number > 0 else "-"


def capital_allocation_pattern(
    cfo: Number | None,
    cfi: Number | None,
    cff: Number | None,
    cfo_quality: Number | None = None,
) -> str:
    """Classify one year from CFO/CFI/CFF signs.

    The (+,-,-) combination is refined to Shareholder Returns when the
    five-year CFO/PAT quality score is above 1.0; otherwise it is Reinvestor.
    """
    signs = (cash_sign(cfo), cash_sign(cfi), cash_sign(cff))

    if signs == ("+", "-", "-"):
        return "Shareholder Returns" if (_number(cfo_quality) or 0) > 1.0 else "Reinvestor"
    labels = {
        ("+", "+", "-"): "Liquidating Assets",
        ("-", "+", "+"): "Distress Signal",
        ("-", "-", "+"): "Growth Funded by Debt",
        ("+", "+", "+"): "Cash Accumulator",
        ("-", "-", "-"): "Pre-Revenue",
        ("+", "-", "+"): "Mixed",
    }
    return labels.get(signs, "Mixed")


def cash_flow_kpis(row: Mapping[str, object], cfo_quality: Number | None = None) -> dict[str, object]:
    """Calculate all Day 11 KPIs for a row-like mapping."""
    fcf = free_cash_flow(
        row.get("cash_from_operating_activity"),
        row.get("cash_from_investing_activity"),
    )
    intensity = capex_intensity(
        row.get("cash_from_investing_activity"),
        row.get("sales"),
    )
    return {
        "free_cash_flow": fcf,
        "cfo_quality_score": cfo_quality,
        "cfo_quality_label": cfo_quality_label(cfo_quality),
        "capex_intensity": intensity,
        "capex_intensity_label": capex_intensity_label(intensity),
        "fcf_conversion_rate": fcf_conversion_rate(fcf, row.get("operating_profit")),
        "capital_allocation_pattern": capital_allocation_pattern(
            row.get("cash_from_operating_activity"),
            row.get("cash_from_investing_activity"),
            row.get("cash_from_financing_activity"),
            cfo_quality,
        ),
    }
