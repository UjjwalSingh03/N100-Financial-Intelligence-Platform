"""Day 33 smoke test: generate and validate five cross-sector tearsheets."""
from pathlib import Path
import sqlite3
import pytest
from src.reports.tearsheet import generate

TICKERS = ("TCS", "HDFCBANK", "RELIANCE", "SUNPHARMA", "TATASTEEL")

@pytest.mark.parametrize("ticker", TICKERS)
def test_two_page_tearsheet(ticker, tmp_path):
    db = Path("db/nifty100.db")
    if not db.exists():
        pytest.skip("Production database not available locally")
    with sqlite3.connect(db) as con:
        if not con.execute("SELECT 1 FROM companies WHERE id=?", (ticker,)).fetchone():
            pytest.skip(f"{ticker} missing from current database")
    pytest.importorskip("reportlab")
    pdf = generate(db, ticker, tmp_path / f"{ticker}.pdf")
    assert pdf.exists() and pdf.stat().st_size > 1000
    from pypdf import PdfReader
    reader = PdfReader(str(pdf))
    assert len(reader.pages) == 2
    assert ticker in (reader.pages[0].extract_text() or "")
    assert "CAPITAL ALLOCATION" in (reader.pages[1].extract_text() or "")
