"""Unit tests for Sprint 2 Day 11 cash-flow KPIs."""

from __future__ import annotations

import pytest

from src.analytics.cash_flow import (
    capital_allocation_pattern,
    capex_intensity,
    capex_intensity_label,
    cfo_quality_label,
    cfo_quality_score,
    fcf_conversion_rate,
    free_cash_flow,
)


def test_free_cash_flow_allows_negative_value() -> None:
    assert free_cash_flow(100, -160) == pytest.approx(-60.0)


def test_cfo_quality_score_averages_five_year_ratios() -> None:
    rows = [
        {"cfo": 120, "pat": 100},
        {"cfo": 110, "pat": 100},
        {"cfo": 90, "pat": 100},
        {"cfo": 130, "pat": 100},
        {"cfo": 100, "pat": 100},
    ]
    assert cfo_quality_score(rows) == pytest.approx(1.1)


def test_cfo_quality_ignores_zero_pat() -> None:
    assert cfo_quality_score([{"cfo": 100, "pat": 0}]) is None


def test_cfo_quality_labels() -> None:
    assert cfo_quality_label(1.1) == "High Quality"
    assert cfo_quality_label(0.75) == "Moderate"
    assert cfo_quality_label(0.4) == "Accrual Risk"


def test_capex_intensity_and_labels() -> None:
    assert capex_intensity(-20, 1000) == pytest.approx(2.0)
    assert capex_intensity_label(2.0) == "Asset Light"
    assert capex_intensity_label(5.0) == "Moderate"
    assert capex_intensity_label(9.0) == "Capital Intensive"


def test_fcf_conversion_zero_operating_profit_returns_none() -> None:
    assert fcf_conversion_rate(100, 0) is None


def test_capital_allocation_reinvestor() -> None:
    assert capital_allocation_pattern(100, -50, -20, 0.9) == "Reinvestor"


def test_capital_allocation_shareholder_returns() -> None:
    assert capital_allocation_pattern(100, -50, -20, 1.2) == "Shareholder Returns"


def test_capital_allocation_remaining_patterns() -> None:
    cases = [
        ((100, 50, -20), "Liquidating Assets"),
        ((-100, 50, 20), "Distress Signal"),
        ((-100, -50, 20), "Growth Funded by Debt"),
        ((100, 50, 20), "Cash Accumulator"),
        ((-100, -50, -20), "Pre-Revenue"),
        ((100, -50, 20), "Mixed"),
    ]
    for values, expected in cases:
        assert capital_allocation_pattern(*values) == expected
