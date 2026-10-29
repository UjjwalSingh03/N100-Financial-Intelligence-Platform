"""14 targeted DQ assertions; DQ-09 negative payout also triggers DQ-10 by design."""
import pandas as pd
import pytest
from src.etl.validator import validate_rules

BASE_COMPANIES={"id":["TCS"],"company_name":["Tata"],"website":["https://example.com"]}
BASE_PL={"id":[1],"company_id":["TCS"],"year":[2024],"sales":[100],"operating_profit":[20],"opm_percentage":[20],"tax_percentage":[20],"eps":[10],"net_profit":[10],"dividend_payout":[20]}
BASE_BS={"id":[1],"company_id":["TCS"],"year":[2024],"total_assets":[100],"total_liabilities":[60],"equity_capital":[20],"reserves":[20]}
BASE_PRICES={"id":[1],"company_id":["TCS"],"date":["2024-03-01"],"close_price":[100]}

@pytest.mark.parametrize("rule,table,changes,severity",[
("DQ-01","companies",{"id":[None]},"CRITICAL"),
("DQ-02","profitandloss",{"id":[1,2],"company_id":["TCS","TCS"],"year":[2024,2024],"sales":[100,100],"operating_profit":[20,20],"opm_percentage":[20,20],"tax_percentage":[20,20],"eps":[10,10],"net_profit":[10,10],"dividend_payout":[20,20]},"CRITICAL"),
("DQ-03","profitandloss",{"company_id":["UNKNOWN"]},"CRITICAL"),
("DQ-04","balancesheet",{"total_assets":[200]},"WARNING"),
("DQ-05","profitandloss",{"opm_percentage":[35]},"WARNING"),
("DQ-06","profitandloss",{"sales":[0],"operating_profit":[0],"opm_percentage":[0]},"WARNING"),
("DQ-07","profitandloss",{"tax_percentage":[101]},"WARNING"),
("DQ-08","profitandloss",{"eps":[1000001]},"WARNING"),
("DQ-09","profitandloss",{"dividend_payout":[-1]},"WARNING"),
("DQ-10","profitandloss",{"dividend_payout":[101]},"WARNING"),
("DQ-11","companies",{"website":["invalid"]},"WARNING"),
("DQ-12","profitandloss",{"eps":[None]},"WARNING"),
("DQ-13","balancesheet",{"total_assets":[0]},"WARNING"),
("DQ-14","profitandloss",{"net_profit":[None]},"WARNING"),
])
def test_rule_violation(rule,table,changes,severity):
    tables={"companies":pd.DataFrame(BASE_COMPANIES),"profitandloss":pd.DataFrame(BASE_PL),
            "balancesheet":pd.DataFrame(BASE_BS),"stock_prices":pd.DataFrame(BASE_PRICES)}
    frame=tables[table].copy()
    required_rows=max([len(value) for value in changes.values()] + [len(frame)])
    if required_rows > len(frame):
        frame=pd.concat([frame] * required_rows, ignore_index=True)
    for key,value in changes.items(): frame[key]=value
    tables[table]=frame
    matches=[f for f in validate_rules(tables) if f.rule_id==rule]
    assert matches and all(f.severity==severity for f in matches)
