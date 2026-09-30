"""Contract tests for the Sprint 3 Day 21 review gate."""
import sqlite3
from pathlib import Path
from scripts.day21_sprint_review import check_peer_rank,check_peer_table,check_quality_compounder

def make_db(tmp_path:Path):
    db=tmp_path/"test.db"
    with sqlite3.connect(db) as con:
        con.executescript("""CREATE TABLE companies(id TEXT PRIMARY KEY,company_name TEXT);
        CREATE TABLE financial_ratios(company_id TEXT,year INTEGER,return_on_equity_pct REAL,debt_to_equity REAL,composite_quality_score REAL);
        CREATE TABLE peer_percentiles(company_id TEXT,peer_group_name TEXT,metric TEXT,value REAL,percentile_rank REAL,year INTEGER);""")
        con.executemany("INSERT INTO companies VALUES (?,?)",[("A","Alpha"),("B","Beta"),("C","Gamma")])
        con.executemany("INSERT INTO financial_ratios VALUES (?,?,?,?,?)",[("A",2025,20,.5,90),("B",2025,25,.8,85),("C",2025,10,.2,70)])
        con.executemany("INSERT INTO peer_percentiles VALUES (?,?,?,?,?,?)",[("A","IT Services","roe",20,.5,2025),("B","IT Services","roe",25,1,2025),("C","IT Services","roe",10,0,2025)])
        groups=[f"G{i}" for i in range(11)]
        for g in groups:
            for metric in ["roe","roce","net_profit_margin","debt_to_equity","free_cash_flow","pat_cagr_5yr","revenue_cagr_5yr","eps_cagr_5yr","interest_coverage","asset_turnover"]:
                con.execute("INSERT INTO peer_percentiles VALUES (?,?,?,?,?,?)",("A",g,metric,1,.5,2025))
    return db

def test_quality_compounder_top_five_condition(tmp_path):
    r=check_quality_compounder(make_db(tmp_path));assert r.status=="PASS";assert "B" in r.detail and "A" in r.detail

def test_it_services_highest_roe_has_highest_percentile(tmp_path):
    assert check_peer_rank(make_db(tmp_path),"IT Services").status=="PASS"

def test_peer_table_requires_11_groups(tmp_path):
    assert check_peer_table(make_db(tmp_path)).status=="PASS"
