"""Unit tests for Sprint 2 Days 08-09 ratio calculations."""

from __future__ import annotations

import logging

import pytest

from src.analytics.ratios import (
    asset_turnover,
    debt_to_equity,
    high_leverage_flag,
    icr_label,
    icr_warning_flag,
    interest_coverage_ratio,
    net_debt,
    net_profit_margin,
    operating_profit_margin,
    return_on_assets,
    return_on_capital_employed,
    return_on_equity,
)


# Day 08
def test_net_profit_margin_normal_case() -> None:
    assert net_profit_margin(150, 1000) == pytest.approx(15.0)


def test_net_profit_margin_zero_sales_returns_none() -> None:
    assert net_profit_margin(150, 0) is None


def test_return_on_equity_normal_case() -> None:
    assert return_on_equity(200, 500, 1500) == pytest.approx(10.0)


def test_return_on_equity_negative_equity_returns_none() -> None:
    assert return_on_equity(200, -1000, 200) is None


def test_return_on_capital_employed_normal_case() -> None:
    assert return_on_capital_employed(300, 500, 1000, 1500) == pytest.approx(10.0)


def test_return_on_assets_normal_case() -> None:
    assert return_on_assets(250, 2500) == pytest.approx(10.0)


def test_return_on_assets_zero_assets_returns_none() -> None:
    assert return_on_assets(250, 0) is None


def test_operating_profit_margin_logs_mismatch(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="src.analytics.ratios"):
        result = operating_profit_margin(180, 1000, source_opm_percentage=15.0)
    assert result == pytest.approx(18.0)
    assert "OPM mismatch" in caplog.text
    assert "difference=3.0000 points" in caplog.text


# Day 09 — Leverage & Efficiency Ratios (8 tests)
def test_debt_to_equity_debt_free_returns_zero() -> None:
    assert debt_to_equity(0, 500, 1500) == pytest.approx(0.0)


def test_debt_to_equity_normal_case() -> None:
    assert debt_to_equity(1000, 500, 1500) == pytest.approx(0.5)


def test_high_leverage_flag_for_non_financials() -> None:
    assert high_leverage_flag(6.0, "Industrials") is True


def test_high_leverage_flag_not_set_for_financials() -> None:
    assert high_leverage_flag(6.0, "Financials") is False


def test_interest_coverage_zero_interest_returns_none() -> None:
    assert interest_coverage_ratio(100, 20, 0) is None


def test_icr_label_is_debt_free_when_icr_is_none() -> None:
    assert icr_label(None) == "Debt Free"


def test_icr_warning_flag_below_1_5() -> None:
    assert icr_warning_flag(1.2) is True


def test_net_debt_and_asset_turnover() -> None:
    assert net_debt(1000, 250) == pytest.approx(750.0)
    assert asset_turnover(2000, 1000) == pytest.approx(2.0)
