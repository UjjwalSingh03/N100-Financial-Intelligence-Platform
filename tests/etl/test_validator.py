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
    assert failures and failures[0].severity == CRITICAL
    assert failures[0].rule_id == "DQ-01"


def test_dq02_composite_key():
    df = pd.DataFrame({"company_id": [1, 1], "year": [2024, 2024]})
    failures = validate_rules({"profitandloss": df})
    assert any(f.rule_id == "DQ-02" for f in failures)


def test_dq03_missing_foreign_key_is_critical():
    child = pd.DataFrame({"company_id": [1, 99]})
    parent = pd.DataFrame({"company_id": [1, 2]})
    failures = validate_foreign_key(child, parent, child_column="company_id", parent_column="company_id", table="profitandloss")
    assert failures and failures[0].severity == CRITICAL


def test_dq04_balance_warning():
    df = pd.DataFrame({"total_assets": [100.0], "total_liabilities": [40.0], "total_equity": [50.0]})
    failures = validate_balance_sheet(df)
    assert failures and failures[0].rule_id == "DQ-04" and failures[0].severity == WARNING


def test_dq05_opm_warning():
    df = pd.DataFrame({"sales": [100.0], "operating_profit": [20.0], "opm": [15.0]})
    failures = validate_opm(df)
    assert failures and failures[0].rule_id == "DQ-05"


def test_dq06_negative_sales_warning():
    df = pd.DataFrame({"sales": [-10.0, 100.0]})
    failures = validate_positive_sales(df)
    assert len(failures) == 1 and failures[0].rule_id == "DQ-06"


def test_optional_rules_run_without_required_columns():
    failures = validate_rules({"companies": pd.DataFrame({"company_id": [1], "website": ["https://example.com"]})})
    assert all(f.rule_id in {"DQ-01", "DQ-11"} for f in failures)


def test_write_validation_failures(tmp_path):
    df = pd.DataFrame({"sales": [0]})
    failures = validate_positive_sales(df)
    output = write_validation_failures(failures, tmp_path / "validation_failures.csv")
    assert output.exists()
    saved = pd.read_csv(output)
    assert saved.loc[0, "rule_id"] == "DQ-06"
