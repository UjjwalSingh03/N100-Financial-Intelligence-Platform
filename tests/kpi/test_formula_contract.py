"""Day 14 KPI formula contract: 20 focused checks for Sprint 2 sign-off."""
import pytest
from src.analytics.ratios import (
    asset_turnover, debt_to_equity, interest_coverage_ratio,
    net_profit_margin, operating_profit_margin, return_on_equity,
)
from src.analytics.cagr import calculate_cagr, cagr_for_window
from src.analytics.cashflow_kpis import (
    capex_intensity, cfo_quality_score, fcf_conversion_rate, free_cash_flow,
)

def test_npm(): assert net_profit_margin(150,1000) == pytest.approx(15)
def test_npm_zero_sales(): assert net_profit_margin(150,0) is None
def test_opm(): assert operating_profit_margin(200,1000,None) == pytest.approx(20)
def test_roe(): assert return_on_equity(100,400,600) == pytest.approx(10)
def test_roe_nonpositive_equity(): assert return_on_equity(100,-500,400) is None
def test_debt_to_equity(): assert debt_to_equity(500,500,1500) == pytest.approx(.25)
def test_debt_free_de(): assert debt_to_equity(0,500,1500) == pytest.approx(0)
def test_icr(): assert interest_coverage_ratio(200,20,40) == pytest.approx(5.5)
def test_icr_zero_interest(): assert interest_coverage_ratio(200,20,0) is None
def test_asset_turnover(): assert asset_turnover(2000,1000) == pytest.approx(2)
def test_asset_turnover_zero_assets(): assert asset_turnover(2000,0) is None
def test_cagr_normal(): assert calculate_cagr(100,121,2).value == pytest.approx(10)
def test_cagr_turnaround(): assert calculate_cagr(-100,150,5).flag == "TURNAROUND"
def test_cagr_decline_to_loss(): assert calculate_cagr(150,-50,5).flag == "DECLINE_TO_LOSS"
def test_cagr_both_negative(): assert calculate_cagr(-150,-75,5).flag == "BOTH_NEGATIVE"
def test_cagr_zero_base(): assert calculate_cagr(0,100,5).flag == "ZERO_BASE"
def test_cagr_insufficient(): assert cagr_for_window([100,110,120],5).flag == "INSUFFICIENT"
def test_fcf(): assert free_cash_flow(100,-40) == pytest.approx(60)
def test_cfo_quality(): assert cfo_quality_score([{"cfo":120,"pat":100},{"cfo":80,"pat":100}]) == pytest.approx(1)
def test_capex_intensity(): assert capex_intensity(-20,1000) == pytest.approx(2)
def test_fcf_conversion(): assert fcf_conversion_rate(80,100) == pytest.approx(80)
