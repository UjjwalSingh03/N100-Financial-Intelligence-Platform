import pandas as pd

from src.etl.validator import (
    CRITICAL,
    WARNING,
    validate_balance_sheet,
    validate_foreign_key,
    validate_opm,
    validate_positive_sales,
    validate_primary_key,
    validate_rules,
    write_validation_failures,
)


def test_dq01_duplicate_primary_key_is_critical():
    df = pd.DataFrame({"id": [1, 1, 2]})
    failures = validate_primary_key(df, "id", table="companies")
    assert len(failures) == 2
    assert all(f.severity == CRITICAL and f.rule_id == "DQ-01" for f in failures)


def test_dq02_composite_key():
    df = pd.DataFrame({"id": [1, 2], "company_id": ["ABB", "ABB"], "year": [2024, 2024]})
    failures = validate_rules({"profitandloss": df})
    assert any(f.rule_id == "DQ-02" for f in failures)


def test_dq03_missing_foreign_key_is_critical():
    child = pd.DataFrame({"company_id": ["ABB", "UNKNOWN"]})
    parent = pd.DataFrame({"id": ["ABB", "TCS"]})
    failures = validate_foreign_key(child, parent, child_column="company_id", parent_column="id", table="profitandloss")
    assert len(failures) == 1
    assert failures[0].severity == CRITICAL


def test_dq04_balance_warning_uses_equity_capital_plus_reserves():
    df = pd.DataFrame({
        "total_liabilities": [100.0],
        "equity_capital": [20.0],
        "reserves": [20.0],
        "total_assets": [100.0],
    })
    failures = validate_balance_sheet(df)
    assert failures and failures[0].rule_id == "DQ-04" and failures[0].severity == WARNING


def test_dq04_balanced_sheet_passes():
    df = pd.DataFrame({
        "total_liabilities": [60.0],
        "equity_capital": [20.0],
        "reserves": [20.0],
        "total_assets": [100.0],
    })
    assert validate_balance_sheet(df) == []


def test_dq05_uses_actual_opm_percentage_column():
    df = pd.DataFrame({"sales": [100.0], "operating_profit": [20.0], "opm_percentage": [15.0]})
    failures = validate_opm(df)
    assert failures and failures[0].rule_id == "DQ-05"


def test_dq06_negative_sales_warning():
    df = pd.DataFrame({"sales": [-10.0, 100.0]})
    failures = validate_positive_sales(df)
    assert len(failures) == 1 and failures[0].rule_id == "DQ-06"


def test_dq07_invalid_tax_percentage():
    df = pd.DataFrame({"id": [1], "company_id": ["ABB"], "year": [2024], "sales": [100],
                       "operating_profit": [20], "opm_percentage": [20], "tax_percentage": [120],
                       "eps": [10], "dividend_payout": [20], "net_profit": [10]})
    failures = validate_rules({"profitandloss": df})
    assert any(f.rule_id == "DQ-07" for f in failures)


def test_dq09_negative_dividend_payout():
    df = pd.DataFrame({"dividend_payout": [-1]})
    failures = validate_rules({"profitandloss": df})
    assert any(f.rule_id == "DQ-09" for f in failures)


def test_dq10_dividend_payout_over_100():
    df = pd.DataFrame({"dividend_payout": [101]})
    failures = validate_rules({"profitandloss": df})
    assert any(f.rule_id == "DQ-10" for f in failures)


def test_dq11_invalid_company_url():
    df = pd.DataFrame({"id": ["ABB"], "website": ["not-a-url"]})
    failures = validate_rules({"companies": df})
    assert any(f.rule_id == "DQ-11" for f in failures)


def test_dq11_valid_company_url_passes():
    df = pd.DataFrame({"id": ["ABB"], "website": ["https://www.abbott.co.in/"]})
    failures = validate_rules({"companies": df})
    assert not any(f.rule_id == "DQ-11" for f in failures)


def test_dq12_missing_eps_is_reported():
    df = pd.DataFrame({"eps": [None]})
    failures = validate_rules({"profitandloss": df})
    assert any(f.rule_id == "DQ-12" for f in failures)


def test_dq13_non_positive_assets():
    df = pd.DataFrame({"total_assets": [0]})
    failures = validate_rules({"balancesheet": df})
    assert any(f.rule_id == "DQ-13" for f in failures)


def test_dq14_missing_net_profit_is_reported():
    df = pd.DataFrame({"net_profit": [None]})
    failures = validate_rules({"profitandloss": df})
    assert any(f.rule_id == "DQ-14" for f in failures)


def test_dq15_non_positive_close_price():
    df = pd.DataFrame({"close_price": [0]})
    failures = validate_rules({"stock_prices": df})
    assert any(f.rule_id == "DQ-15" for f in failures)


def test_dq16_invalid_price_date():
    df = pd.DataFrame({"date": ["not-a-date"]})
    failures = validate_rules({"stock_prices": df})
    assert any(f.rule_id == "DQ-16" for f in failures)


def test_valid_price_date_passes():
    df = pd.DataFrame({"date": ["2024-01-02"]})
    failures = validate_rules({"stock_prices": df})
    assert not any(f.rule_id == "DQ-16" for f in failures)


def test_write_validation_failures(tmp_path):
    df = pd.DataFrame({"sales": [0]})
    failures = validate_positive_sales(df)
    output = write_validation_failures(failures, tmp_path / "validation_failures.csv")
    assert output.exists()
    saved = pd.read_csv(output)
    assert saved.loc[0, "rule_id"] == "DQ-06"
