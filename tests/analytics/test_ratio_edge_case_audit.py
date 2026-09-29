"""Day 13 contract tests."""
from pathlib import Path
import sqlite3

from scripts.ratio_edge_case_audit import audit


def _db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript("""
    CREATE TABLE companies (
        id TEXT PRIMARY KEY,
        company_name TEXT,
        broad_sector TEXT,
        roce_percentage REAL,
        roe_percentage REAL
    );
    CREATE TABLE profitandloss (
        id INTEGER PRIMARY KEY,
        company_id TEXT,
        year INTEGER,
        operating_profit REAL,
        net_profit REAL
    );
    CREATE TABLE balancesheet (
        id INTEGER PRIMARY KEY,
        company_id TEXT,
        year INTEGER,
        equity_capital REAL,
        reserves REAL,
        borrowings REAL
    );
    """)
    conn.executemany("INSERT INTO companies VALUES (?,?,?,?,?)", [
        ("BANK1","Bank One","Financials",8.0,12.0),
        ("TECH1","Tech One","Technology",30.0,20.0),
    ])
    conn.executemany("INSERT INTO profitandloss VALUES (?,?,?,?,?)", [
        ("1","BANK1",2025,20,10), ("2","TECH1",2025,20,10),
    ])
    conn.executemany("INSERT INTO balancesheet VALUES (?,?,?,?,?,?)", [
        ("1","BANK1",2025,10,10,500), ("2","TECH1",2025,10,10,20),
    ])
    conn.commit()
    conn.close()


def test_financials_high_leverage_is_suppressed():
    assert __import__("src.analytics.ratios", fromlist=["high_leverage_flag"]).high_leverage_flag(25, "Financials") is False


def test_audit_logs_roce_anomaly(tmp_path: Path):
    db = tmp_path / "test.db"
    log = tmp_path / "ratio_edge_cases.log"
    _db(db)
    result = audit(db, log)
    assert result["financials"] == 1
    assert result["roce_anomalies"] == 2
    text = log.read_text(encoding="utf-8")
    assert "ROCE | company_id=BANK1" in text
    assert "category=formula discrepancy" in text
