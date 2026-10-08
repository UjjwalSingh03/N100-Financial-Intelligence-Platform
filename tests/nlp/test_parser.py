"""Day 29 contract tests for the NLP analysis parser."""

import sqlite3

import pandas as pd

from src.nlp.parser import PATTERN, cross_validate, parse_analysis_frame, parse_text


def test_required_regex_extracts_period_and_value():
    assert PATTERN.search("10 Years: 21%")
    assert parse_text("10 Years: 21%") == [(10, 21.0)]
    assert parse_text("5 Years: 14.5%") == [(5, 14.5)]
    assert parse_text("3 Years 8.2%") == [(3, 8.2)]


def test_parser_extracts_all_target_fields():
    frame = pd.DataFrame([{
        "id": "TCS",
        "compounded_sales_growth": "10 Years: 21%",
        "compounded_profit_growth": "5 Years: 18.5%",
        "stock_price_cagr": "3 Years: 12%",
        "roe": "10 Years: 27.5%",
    }])

    parsed, failures = parse_analysis_frame(frame)

    assert len(parsed) == 4
    assert set(parsed["metric_type"]) == {
        "compounded_sales_growth",
        "compounded_profit_growth",
        "stock_price_cagr",
        "roe",
    }
    assert failures.empty


def test_unmatched_text_goes_to_failures():
    frame = pd.DataFrame([{
        "company_id": "INFY",
        "compounded_sales_growth": "Not Available",
        "compounded_profit_growth": "5 Years: 12%",
        "stock_price_cagr": None,
        "roe": "NA",
    }])

    parsed, failures = parse_analysis_frame(frame)

    assert len(parsed) == 1
    assert len(failures) == 2
    assert set(failures["metric_type"]) == {
        "compounded_sales_growth",
        "roe",
    }


def test_cross_validation_flags_more_than_five_percentage_points():
    parsed = pd.DataFrame([
        {
            "company_id": "TCS",
            "metric_type": "compounded_sales_growth",
            "period_years": 5,
            "value_pct": 21.0,
        },
        {
            "company_id": "TCS",
            "metric_type": "compounded_profit_growth",
            "period_years": 5,
            "value_pct": 10.0,
        },
        {
            "company_id": "INFY",
            "metric_type": "compounded_sales_growth",
            "period_years": 5,
            "value_pct": 20.0,
        },
    ])
    ratios = pd.DataFrame([
        {
            "company_id": "TCS",
            "year": 2024,
            "revenue_cagr_5yr": 14.0,
            "pat_cagr_5yr": 10.0,
        },
        {
            "company_id": "INFY",
            "year": 2024,
            "revenue_cagr_5yr": 20.0,
            "pat_cagr_5yr": 8.0,
        },
    ])

    divergences = cross_validate(parsed, ratios)

    assert len(divergences) == 1
    assert divergences.iloc[0]["company_id"] == "TCS"
    assert divergences.iloc[0]["metric_type"] == "compounded_sales_growth"
    assert divergences.iloc[0]["review_flag"] == "MANUAL_REVIEW"


def test_cross_validation_ignores_non_five_year_values():
    parsed = pd.DataFrame([{
        "company_id": "TCS",
        "metric_type": "compounded_sales_growth",
        "period_years": 10,
        "value_pct": 30.0,
    }])
    ratios = pd.DataFrame([{
        "company_id": "TCS",
        "year": 2024,
        "revenue_cagr_5yr": 10.0,
        "pat_cagr_5yr": 8.0,
    }])

    assert cross_validate(parsed, ratios).empty


def test_cross_validation_with_latest_sqlite_row(tmp_path):
    db_path = tmp_path / "nifty100.db"
    con = sqlite3.connect(db_path)
    con.execute(
        "CREATE TABLE financial_ratios (company_id TEXT, year INTEGER, "
        "revenue_cagr_5yr REAL, pat_cagr_5yr REAL)"
    )
    con.executemany(
        "INSERT INTO financial_ratios VALUES (?, ?, ?, ?)",
        [
            ("TCS", 2023, 10.0, 9.0),
            ("TCS", 2024, 14.0, 10.0),
        ],
    )
    con.commit()
    con.close()

    from src.nlp.parser import read_ratio_values

    ratios = read_ratio_values(db_path)
    assert len(ratios) == 1
    assert int(ratios.iloc[0]["year"]) == 2024
