"""Tests for Day 31 cash-flow intelligence integration."""
from __future__ import annotations

import sqlite3

import pandas as pd

from src.analytics.cashflow_kpis import calculate_cashflow_intelligence, generate


def _db(path):
    with sqlite3.connect(path) as con:
        con.executescript("""
        CREATE TABLE companies (id TEXT PRIMARY KEY, company_name TEXT, sector TEXT);
        CREATE TABLE profitandloss (company_id TEXT, year INTEGER, sales REAL, net_profit REAL);
        CREATE TABLE cashflow (company_id TEXT, year INTEGER, cash_from_operating_activity REAL,
            cash_from_investing_activity REAL, cash_from_financing_activity REAL);
        CREATE TABLE balancesheet (company_id TEXT, year INTEGER, borrowings REAL);
        CREATE TABLE financial_ratios (company_id TEXT, year INTEGER, free_cash_flow_cr REAL);
        """)
        con.executemany("INSERT INTO companies VALUES (?,?,?)", [
            ("AAA", "Alpha", "IT"), ("BBB", "Beta", "Energy")
        ])
        # AAA: CFO/PAT average = 1.2; distress in latest year.
        for year, pat, cfo, cfi, cff, debt in [
            (2019, 100, 110, -2, 5, 100), (2020, 100, 120, -3, 4, 95),
            (2021, 100, 130, -3, 3, 90), (2022, 100, 140, -4, 2, 85),
            (2023, 100, 150, -4, 10, 80), (2024, 100, -10, -4, 20, 75),
        ]:
            con.execute("INSERT INTO profitandloss VALUES (?,?,?,?)", ("AAA", year, 1000, pat))
            con.execute("INSERT INTO cashflow VALUES (?,?,?,?,?)", ("AAA", year, cfo, cfi, cff))
            con.execute("INSERT INTO balancesheet VALUES (?,?,?)", ("AAA", year, debt))
            con.execute("INSERT INTO financial_ratios VALUES (?,?,?)", ("AAA", year, cfo+cfi))
        # BBB: latest year has CFO positive and debt declining with financing outflow.
        for year, cfo, cfi, cff, debt in [(2023, 100, -20, -10, 100), (2024, 120, -30, -15, 80)]:
            con.execute("INSERT INTO profitandloss VALUES (?,?,?,?)", ("BBB", year, 500, 80))
            con.execute("INSERT INTO cashflow VALUES (?,?,?,?,?)", ("BBB", year, cfo, cfi, cff))
            con.execute("INSERT INTO balancesheet VALUES (?,?,?)", ("BBB", year, debt))
            con.execute("INSERT INTO financial_ratios VALUES (?,?,?)", ("BBB", year, cfo+cfi))


def test_calculates_one_row_per_company_and_distress_alert(tmp_path):
    db = tmp_path / "cashflow.db"
    _db(db)
    data, alerts = calculate_cashflow_intelligence(db)
    assert len(data) == 2
    aaa = data.set_index("company_id").loc["AAA"]
    assert aaa["cfo_quality_label"] == "High Quality"
    assert bool(aaa["distress_flag"])
    assert bool(data.set_index("company_id").loc["BBB", "deleveraging_flag"])
    assert alerts["company_id"].tolist() == ["AAA"]
    assert alerts.iloc[0]["cfo_value"] == -10
    assert alerts.iloc[0]["cff_value"] == 20
    assert alerts.iloc[0]["latest_net_profit"] == 100


def test_generates_requested_files_and_columns(tmp_path):
    db = tmp_path / "cashflow.db"
    _db(db)
    workbook, alerts = generate(db, tmp_path / "output")
    assert workbook.exists() and alerts.exists()
    assert list(pd.read_excel(workbook).columns) == [
        "company_id", "sector", "cfo_quality_score", "cfo_quality_label",
        "capex_intensity_pct", "capex_label", "fcf_cagr_5yr",
        "fcf_conversion_pct", "distress_flag", "deleveraging_flag",
        "capital_allocation_label",
    ]
    assert list(pd.read_csv(alerts).columns) == [
        "company_id", "sector", "cfo_value", "cff_value", "latest_net_profit"
    ]
