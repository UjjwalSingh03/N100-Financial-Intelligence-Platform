"""Unit tests for Sprint 2 Day 10 CAGR engine."""

from __future__ import annotations

import pytest

from src.analytics.cagr import (
    CAGRResult,
    calculate_cagr,
    cagr_columns,
    cagr_for_window,
    growth_metrics_all,
)


def test_normal_cagr() -> None:
    result = calculate_cagr(100, 121, 2)
    assert result.value == pytest.approx(10.0)
    assert result.flag is None


def test_three_year_window_normal_cagr() -> None:
    result = cagr_for_window([100, 105, 110, 133.1], 3)
    assert result.value == pytest.approx(10.0)
    assert result.flag is None


def test_turnaround_flag() -> None:
    result = calculate_cagr(-100, 150, 5)
    assert result == CAGRResult(None, "TURNAROUND")


def test_decline_to_loss_flag() -> None:
    result = calculate_cagr(150, -50, 5)
    assert result == CAGRResult(None, "DECLINE_TO_LOSS")


def test_both_negative_flag() -> None:
    result = calculate_cagr(-150, -75, 5)
    assert result == CAGRResult(None, "BOTH_NEGATIVE")


def test_zero_base_flag() -> None:
    result = calculate_cagr(0, 100, 5)
    assert result == CAGRResult(None, "ZERO_BASE")


def test_insufficient_data_flag() -> None:
    result = cagr_for_window([100, 105, 110], 5)
    assert result == CAGRResult(None, "INSUFFICIENT")


def test_end_zero_is_decline_to_loss() -> None:
    result = calculate_cagr(100, 0, 3)
    assert result == CAGRResult(None, "DECLINE_TO_LOSS")


def test_all_growth_metrics_have_required_windows() -> None:
    values = [100, 110, 121, 133.1, 146.41, 161.051, 177.1561, 194.8717, 214.3589, 235.7948, 259.3742]
    result = growth_metrics_all(values, values, values)
    assert set(result) == {
        "revenue_cagr_3yr", "revenue_cagr_5yr", "revenue_cagr_10yr",
        "pat_cagr_3yr", "pat_cagr_5yr", "pat_cagr_10yr",
        "eps_cagr_3yr", "eps_cagr_5yr", "eps_cagr_10yr",
    }


def test_cagr_columns_store_value_and_separate_flag() -> None:
    revenue = [100, 110, 121, 133.1, 146.41, 161.051]
    pat = [100, 110, 121, 133.1, 146.41, 161.051]
    eps = [100, 110, 121, 133.1, 146.41, 161.051]
    columns = cagr_columns(revenue, pat, eps)
    assert columns["revenue_cagr_5yr"] == pytest.approx(10.0)
    assert columns["revenue_cagr_5yr_flag"] is None
