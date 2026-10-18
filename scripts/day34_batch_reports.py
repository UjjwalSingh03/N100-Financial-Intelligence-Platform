"""Day 34 batch generation for both normalized and dashboard-compatible N100 databases."""
from __future__ import annotations
import argparse
import csv
import re
import sqlite3
import tempfile
from collections import defaultdict
from pathlib import Path
from statistics import median
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle, Spacer, PageBreak
from src.reports.tearsheet import generate

METRICS = ("Revenue", "Net Profit", "OPM %", "ROE %", "D/E", "EPS", "CFO", "FCF")
STYLE = ParagraphStyle("wrapped", fontName="Helvetica", fontSize=7, leading=10, wordWrap="CJK")


def year(value):
    m = re.search(r"(?:19|20)\d{2}|(?<=-)\d{2}$", str(value))
    if not m: return None
    s = m.group()
    return int(s) if len(s) == 4 else 2000 + int(s)


def normalized_copy(source, target):
    """Adapt dashboard source names and date formats without modifying the original DB."""
    src = sqlite3.connect(source); src.row_factory = sqlite3.Row
    dst = sqlite3.connect(target)
    dst.executescript("""
    CREATE TABLE companies(id TEXT PRIMARY KEY,company_name TEXT,ticker TEXT,sector TEXT);
    CREATE TABLE profitandloss(company_id TEXT,year INTEGER,sales REAL,operating_profit REAL,opm_percentage REAL,net_profit REAL,eps REAL);
    CREATE TABLE balancesheet(company_id TEXT,year INTEGER,equity_capital REAL,reserves REAL,borrowings REAL,other_liabilities REAL);
    CREATE TABLE cashflow(company_id TEXT,year INTEGER,cash_from_operating_activity REAL,cash_from_investing_activity REAL,cash_from_financing_activity REAL,net_cash_flow REAL);
    CREATE TABLE financial_ratios(company_id TEXT,year INTEGER,return_on_equity_pct REAL,debt_to_equity REAL,roce_percentage REAL);
    CREATE TABLE prosandcons(company_id TEXT,item_type TEXT,description TEXT,id INTEGER);
    """)
    def has(t): return bool(src.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone())
    sectors = {r["company_id"]: r["broad_sector"] for r in src.execute("SELECT company_id,broad_sector FROM sectors")} if has("sectors") else {}
    companies = [dict(r) for r in src.execute("SELECT * FROM companies")]
    dst.executemany("INSERT INTO companies VALUES (?,?,?,?)", [(r["id"],r.get("company_name"),r["id"],sectors.get(r["id"],r.get("sector","Unknown"))) for r in companies])
    mapping = [
        ("profitandloss","profit_and_loss",("sales","operating_profit","opm_percentage","net_profit","eps")),
        ("balancesheet","balance_sheet",("equity_capital","reserves","borrowings","other_liabilities")),
        ("cashflow","cash_flow",("cash_from_operating_activity","cash_from_investing_activity","cash_from_financing_activity","net_cash_flow")),
        ("financial_ratios","financial_ratios",("return_on_equity_pct","debt_to_equity","roce_percentage"))]
    aliases = {"cash_from_operating_activity":"operating_activity","cash_from_investing_activity":"investing_activity","cash_from_financing_activity":"financing_activity"}
    for dest, alternate, fields in mapping:
        source_table = dest if has(dest) else alternate
        if not has(source_table): continue
        cols = {r[1] for r in src.execute(f"PRAGMA table_info({source_table})")}
        seen = set()
        for r in src.execute(f"SELECT * FROM {source_table}"):
            r=dict(r); yr=year(r.get("year")); key=(r["company_id"],yr)
            if yr is None or key in seen: continue
            seen.add(key)
            vals=[r.get(aliases.get(f,f)) if aliases.get(f,f) in cols else None for f in fields]
            dst.execute(f"INSERT INTO {dest} VALUES ({','.join('?' for _ in range(2+len(fields)))})",(r["company_id"],yr,*vals))
    if has("prosandcons"):
        for r in src.execute("SELECT company_id,item_type,description,id FROM prosandcons"):
            dst.execute("INSERT INTO prosandcons VALUES (?,?,?,?)",tuple(r))
    elif has("pros_and_cons"):
        i=0
        for r in src.execute("SELECT company_id,pros,cons FROM pros_and_cons"):
            for kind in ("pros","cons"):
                if r[kind]:
                    i+=1;dst.execute("INSERT INTO prosandcons VALUES (?,?,?,?)",(r["company_id"],kind,r[kind],i))
    dst.commit();src.close();dst.close()


def sector_report(path, sector, companies, con):
    doc=SimpleDocTemplate(str(path),pagesize=(595,842),leftMargin=30,rightMargin=30,topMargin=35,bottomMargin=35)
    def para(s): return Paragraph(escape(str(s)),STYLE)
    records=[]
    for ticker in companies:
        p=con.execute("SELECT * FROM profitandloss WHERE company_id=? ORDER BY year DESC LIMIT 1",(ticker,)).fetchone()
        r=con.execute("SELECT * FROM financial_ratios WHERE company_id=? ORDER BY year DESC LIMIT 1",(ticker,)).fetchone()
        cf=con.execute("SELECT * FROM cashflow WHERE company_id=? ORDER BY year DESC LIMIT 1",(ticker,)).fetchone()
        p=dict(p) if p else {};r=dict(r) if r else {};cf=dict(cf) if cf else {}
        cfo=cf.get("cash_from_operating_activity");cfi=cf.get("cash_from_investing_activity")
        records.append([p.get("sales"),p.get("net_profit"),p.get("opm_percentage"),r.get("return_on_equity_pct"),
                        r.get("debt_to_equity"),p.get("eps"),cfo,cfo+cfi if cfo is not None and cfi is not None else None])
    med=[median([float(row[i]) for row in records if row[i] is not None]) if any(row[i] is not None for row in records) else None for i in range(8)]
    story=[Paragraph(escape(sector)+" — Sector Report",ParagraphStyle("heading",fontName="Helvetica-Bold",fontSize=16,leading=20,wordWrap="CJK")),
           Spacer(1,16),para(f"Companies: {len(companies)} | Median KPIs"),Spacer(1,8)]
    summary=Table([[para(k),para(f"{v:,.2f}" if v is not None else "N/A")] for k,v in zip(METRICS,med)],colWidths=[210,290])
    summary.setStyle(TableStyle([("WORDWRAP",(0,0),(-1,-1),"CJK"),("GRID",(0,0),(-1,-1),.25,colors.lightgrey),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.extend([summary,PageBreak(),para("Company metrics (latest available annual record)"),Spacer(1,8)])
    data=[[para(k) for k in ("Ticker",*METRICS)]]
    for ticker,values in zip(companies,records):
        data.append([para(ticker)]+[para(f"{v:,.1f}" if v is not None else "N/A") for v in values])
    widths=[70]+[58]*8
    table=Table(data,colWidths=widths,repeatRows=1,hAlign="LEFT")
    table.setStyle(TableStyle([("WORDWRAP",(0,0),(-1,-1),"CJK"),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#122744")),
                               ("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.2,colors.lightgrey),
                               ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),3),("RIGHTPADDING",(0,0),(-1,-1),3)]))
    story.append(table);doc.build(story)


def run(db_path="db/nifty100.db", output_root="reports", audit_dir="output", capital_csv="output/capital_allocation.csv"):
    output_root=Path(output_root);audit_dir=Path(audit_dir)
    (output_root/"tearsheets").mkdir(parents=True,exist_ok=True)
    (output_root/"sector").mkdir(parents=True,exist_ok=True);audit_dir.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        db=Path(temp)/"normalized.db";normalized_copy(db_path,db)
        con=sqlite3.connect(db);con.row_factory=sqlite3.Row
        companies=[dict(r) for r in con.execute("SELECT * FROM companies ORDER BY id")]
        skipped=[]; generated=[]; failures=[]
        for c in companies:
            ticker=c["id"]
            years=con.execute("SELECT COUNT(DISTINCT year) FROM profitandloss WHERE company_id=?",(ticker,)).fetchone()[0]
            if years<3:
                skipped.append({"company_id":ticker,"years":years,"reason":"Fewer than 3 P&L years"});continue
            path=output_root/"tearsheets"/f"{ticker}_tearsheet.pdf"
            try:
                generate(db,ticker,path,capital_csv);generated.append(ticker)
            except Exception as exc:
                failures.append({"company_id":ticker,"reason":str(exc)})
        with (audit_dir/"skipped_tearsheets.csv").open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["company_id","years","reason"]);w.writeheader();w.writerows(skipped)
        with (audit_dir/"failed_tearsheets.csv").open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["company_id","reason"]);w.writeheader();w.writerows(failures)
        groups=defaultdict(list)
        for c in companies: groups[c["sector"] or "Unknown"].append(c["id"])
        for i,(sector,tickers) in enumerate(sorted(groups.items()),1):
            slug=re.sub(r"[^a-z0-9]+","_",sector.lower()).strip("_") or f"sector_{i}"
            sector_report(output_root/"sector"/f"{slug}_report.pdf",sector,tickers,con)
        con.close()
    print(f"Tearsheets: {len(generated)} | Skipped: {len(skipped)} | Failed: {len(failures)} | Sector PDFs: {len(groups)}")
    if failures: raise RuntimeError("See output/failed_tearsheets.csv")
    return len(generated),len(skipped),len(groups)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--db",default="db/nifty100.db")
    p.add_argument("--output-root",default="reports");p.add_argument("--audit-dir",default="output")
    p.add_argument("--capital-csv",default="output/capital_allocation.csv")
    a=p.parse_args();run(a.db,a.output_root,a.audit_dir,a.capital_csv)
