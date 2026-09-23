"""Unit tests for Sprint 2 Day 08 profitability ratios."""

from __future__ import annotations

import logging

import pytest

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    return_on_assets,
    return_on_capital_employed,
    return_on_equity,
)


# 1. Normal NPM calculation
def test_net_profit_margin_normal_case() -> None:
    assert net_profit_margin(150, 1000) == pytest.approx(15.0)


# 2. Zero sales denominator

def test_net_profit_margin_zero_sales_returns_none() -> None:
    assert net_profit_margin(150, 0) is None


# 3. Normal ROE calculation

def test_return_on_equity_normal_case() -> None:
    assert return_on_equity(200, 500, 1500) == pytest.approx(10.0)


# 4. Negative equity denominator

def test_return_on_equity_negative_equity_returns_none() -> None:
    assert return_on_equity(200, -1000, 200) is None


# 5. Normal ROCE calculation

def test_return_on_capital_employed_normal_case() -> None:
    assert return_on_capital_employed(300, 500, 1000, 1500) == pytest.approx(10.0)


# 6. Normal ROA calculation

def test_return_on_assets_normal_case() -> None:
    assert return_on_assets(250, 2500) == pytest.approx(10.0)


# 7. Zero assets denominator

def test_return_on_assets_zero_assets_returns_none() -> None:
    assert return_on_assets(250, 0) is None


# 8. OPM source cross-check mismatch logging

def test_operating_profit_margin_logs_mismatch(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="src.analytics.ratios"):
        result = operating_profit_margin(180, 1000, source_opm_percentage=15.0)

    assert result == pytest.approx(18.0)
    assert "OPM mismatch" in caplog.text
    assert "difference=3.0000 points" in caplog.text
