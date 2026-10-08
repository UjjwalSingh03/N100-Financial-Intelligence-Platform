import sqlite3
from pathlib import Path
import pandas as pd
from src.nlp.pros_cons_generator import CONFIDENCE_THRESHOLD, generate_for_company, generate

def positive_fixture():
    row=pd.Series({"sector":"IT Services","return_on_equity_pct":25,"debt_to_equity":0,
        "free_cash_flow_cr":12,"operating_profit_margin_pct":30,"revenue_cagr_5yr":18,
        "pat_cagr_5yr":25,"eps_cagr_5yr":20,"interest_coverage":12,
        "dividend_yield_pct":2.5,"dividend_payout_ratio_pct":60,"net_profit":10,
        "roce_percentage":15,"sales":120,"operating_profit":36,"borrowings":0,
        "total_assets":120})
    h=pd.DataFrame([
        {"year":2018,"sales":80,"opm_percentage":20,"operating_profit_margin_pct":20,"net_profit":8,"earnings_per_share":8,"return_on_equity_pct":21,"debt_to_equity":1,"free_cash_flow_cr":8,"total_assets":80,"borrowings":20},
        {"year":2019,"sales":90,"opm_percentage":21,"operating_profit_margin_pct":21,"net_profit":9,"earnings_per_share":9,"return_on_equity_pct":22,"debt_to_equity":.9,"free_cash_flow_cr":9,"total_assets":90,"borrowings":18},
        {"year":2020,"sales":100,"opm_percentage":22,"operating_profit_margin_pct":22,"net_profit":10,"earnings_per_share":10,"return_on_equity_pct":23,"debt_to_equity":.8,"free_cash_flow_cr":10,"total_assets":100,"borrowings":16},
        {"year":2021,"sales":110,"opm_percentage":23,"operating_profit_margin_pct":23,"net_profit":11,"earnings_per_share":11,"return_on_equity_pct":24,"debt_to_equity":.7,"free_cash_flow_cr":11,"total_assets":110,"borrowings":14},
        {"year":2022,"sales":120,"opm_percentage":24,"operating_profit_margin_pct":24,"net_profit":12,"earnings_per_share":12,"return_on_equity_pct":25,"debt_to_equity":.6,"free_cash_flow_cr":12,"total_assets":120,"borrowings":12},
    ])
    return row,h

def test_positive_rules_and_confidence():
    row,h=positive_fixture()
    ids={x["rule_id"] for x in generate_for_company(row,h,False)}
    assert {"P01","P02","P03","P04","P05","P06","P07","P08","P09","P10","P11","P12"} <= ids
    assert all(x["confidence_pct"]>CONFIDENCE_THRESHOLD for x in generate_for_company(row,h,False))

def test_negative_rules():
    row=pd.Series({"sector":"IT Services","debt_to_equity":3.5,"free_cash_flow_cr":-10,
        "operating_profit_margin_pct":10,"net_profit":-5,"interest_coverage":1,
        "dividend_payout_ratio_pct":120,"roce_percentage":5,"revenue_cagr_5yr":2,
        "sales":100,"operating_profit":10,"borrowings":500,"cash_and_equivalents":0})
    h=pd.DataFrame([
        {"year":2020,"sales":120,"operating_profit_margin_pct":18,"free_cash_flow_cr":-10,"debt_to_equity":1,"earnings_per_share":10},
        {"year":2021,"sales":110,"operating_profit_margin_pct":16,"free_cash_flow_cr":-5,"debt_to_equity":2,"earnings_per_share":9},
        {"year":2022,"sales":100,"operating_profit_margin_pct":14,"free_cash_flow_cr":-1,"debt_to_equity":3,"earnings_per_share":8},
    ])
    ids={x["rule_id"] for x in generate_for_company(row,h,False)}
    assert {"C01","C02","C03","C04","C05","C06","C07","C08","C09","C10","C11","C12"} <= ids

def test_strict_coverage_rejects_missing_signal(tmp_path:Path):
    db=tmp_path/"t.db"; c=sqlite3.connect(db)
    c.executescript("""CREATE TABLE companies(id TEXT PRIMARY KEY,company_name TEXT,sector TEXT);
    CREATE TABLE financial_ratios(id INTEGER,company_id TEXT,year INTEGER,return_on_equity_pct REAL,operating_profit_margin_pct REAL,debt_to_equity REAL,interest_coverage REAL,free_cash_flow_cr REAL,earnings_per_share REAL,dividend_payout_ratio_pct REAL,revenue_cagr_5yr REAL,pat_cagr_5yr REAL,eps_cagr_5yr REAL,total_debt_cr REAL);
    CREATE TABLE profitandloss(company_id TEXT,year INTEGER,sales REAL,operating_profit REAL,opm_percentage REAL,net_profit REAL,eps REAL,depreciation REAL);
    CREATE TABLE balancesheet(company_id TEXT,year INTEGER,borrowings REAL,total_assets REAL);
    CREATE TABLE cashflow(company_id TEXT,year INTEGER,cash_from_operating_activity REAL);
    INSERT INTO companies VALUES('X','X Co','IT Services');
    INSERT INTO financial_ratios VALUES(1,'X',2024,10,20,1,5,10,5,50,10,10,10,100);
    INSERT INTO profitandloss VALUES('X',2024,100,20,20,10,5,2);
    INSERT INTO balancesheet VALUES('X',2024,20,100);
    INSERT INTO cashflow VALUES('X',2024,20);"""); c.commit(); c.close()
    try: generate(db,tmp_path/"out.csv",strict=True)
    except ValueError as e: assert "Coverage validation failed" in str(e)
    else: raise AssertionError("strict coverage should fail")

def test_output_contract(tmp_path:Path):
    out=tmp_path/"x.csv"
    row,h=positive_fixture()
    assert set(pd.DataFrame(generate_for_company(row,h,False)).columns)==set(["type","rule_id","text","confidence_pct"])
