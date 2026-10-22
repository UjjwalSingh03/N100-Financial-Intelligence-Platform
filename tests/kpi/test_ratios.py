import logging
import pytest
from src.analytics import ratios as r
from src.analytics.cagr import calculate_cagr
from src.analytics.cash_flow import cfo_quality_score

@pytest.mark.parametrize("profit,equity,reserves,expected",[(20,50,50,20),(0,50,50,0),(-10,50,50,-10),(20,-100,50,None),(20,0,0,None),(None,50,50,None)])
def test_roe(profit,equity,reserves,expected):
    assert r.return_on_equity(profit,equity,reserves)==expected

@pytest.mark.parametrize("debt,equity,reserves,expected",[(0,100,0,0),(50,50,50,.5),(100,0,0,None)])
def test_debt_equity(debt,equity,reserves,expected):
    assert r.debt_to_equity(debt,equity,reserves)==expected

@pytest.mark.parametrize("operating,other,interest,expected",[(100,20,0,None),(100,20,20,6)])
def test_icr(operating,other,interest,expected):
    assert r.interest_coverage_ratio(operating,other,interest)==expected

@pytest.mark.parametrize("de,sector,expected",[(6,"IT",True),(6,"Financials",False),(5,"IT",False)])
def test_leverage_flag(de,sector,expected):
    assert r.high_leverage_flag(de,sector) is expected

@pytest.mark.parametrize("start,end,years,flag,value",[(-10,10,5,"TURNAROUND",None),(10,-10,5,"DECLINE_TO_LOSS",None),(100,121,2,None,10),(0,10,5,"ZERO_BASE",None)])
def test_cagr(start,end,years,flag,value):
    actual=calculate_cagr(start,end,years)
    assert actual.flag==flag
    if value is None: assert actual.value is None
    else: assert actual.value==pytest.approx(value)

def test_opm_divergence(caplog):
    with caplog.at_level(logging.WARNING):
        assert r.operating_profit_margin(30,100,20)==30
    assert "OPM mismatch" in caplog.text

def test_cfo_quality():
    assert cfo_quality_score([{"cfo":120,"pat":100},{"cfo":80,"pat":100}])==pytest.approx(1)
