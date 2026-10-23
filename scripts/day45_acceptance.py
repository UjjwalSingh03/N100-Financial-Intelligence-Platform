"""Day 45 strict acceptance runner: no unverified gate can pass.

Run locally: python -m scripts.day45_acceptance
Manual evidence is supplied in output/day45_manual_evidence.json as booleans
only after human inspection. The script never signs on behalf of a team lead.
"""
import csv
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]
DB=Path(os.getenv("N100_DB_PATH",ROOT/"db/nifty100.db"))
OUT=ROOT/"output"
REPORT=OUT/"day45_gate_results.json"
def main():
    """Evaluate gates conservatively and save explicit PASS/FAIL evidence."""
    manual=OUT/"day45_manual_evidence.json"
    evidence=json.loads(manual.read_text()) if manual.exists() else {}
    results={}
    def gate(n,ok,detail):
        results[f"AC-{n:02d}"]={"status":"PASS" if ok else "FAIL","evidence":str(detail)}
    if not DB.is_file():
        for n in range(1,20): gate(n,False,"Current production database missing; no verified result")
    else:
        with sqlite3.connect(f"file:{DB.resolve().as_posix()}?mode=ro",uri=True) as db:
            names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            def count(t): return db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] if t in names else None
            companies=count("companies")
            gate(1,companies==92,f"companies={companies}")
            coverage={}
            for t in ("profitandloss","balancesheet","cashflow"):
                coverage[t]=db.execute(f"SELECT COUNT(*) FROM (SELECT company_id FROM {t} GROUP BY company_id HAVING COUNT(DISTINCT year)>=10)").fetchone()[0] if t in names else None
            joint=None
            if all(t in names for t in coverage):
                joint=db.execute("""SELECT COUNT(*) FROM companies c WHERE
                (SELECT COUNT(DISTINCT year) FROM profitandloss WHERE company_id=c.id)>=10 AND
                (SELECT COUNT(DISTINCT year) FROM balancesheet WHERE company_id=c.id)>=10 AND
                (SELECT COUNT(DISTINCT year) FROM cashflow WHERE company_id=c.id)>=10""").fetchone()[0]
            gate(2,joint is not None and companies==92 and joint>=83,f"joint 10-year coverage={joint}/92; individual={coverage}")
            fk=db.execute("PRAGMA foreign_key_check").fetchall()
            gate(3,len(fk)==0,f"foreign_key_check rows={len(fk)}")
            ratios=count("financial_ratios")
            gate(4,ratios is not None and ratios>=1100,f"financial_ratios={ratios}")
            peers=db.execute("SELECT COUNT(DISTINCT peer_group_name) FROM peer_percentiles").fetchone()[0] if "peer_percentiles" in names else None
            gate(14,peers==11,f"peer groups with percentiles={peers}")
    for n,label in [(5,"manual Excel revenue CAGR spot-check <=0.1 percentage points"),(6,"five source ROE comparisons <=5%"),(7,"Quality preset 10-50"),(8,"Profile full screen <3s"),(9,"screener CSV valid"),(10,"five PDF overflow visual inspections"),(11,"API health HTTP 200"),(12,"TCS ratios >=10 years"),(13,"API/screener Excel ID parity")]:
        gate(n,evidence.get(f"AC-{n:02d}") is True,f"{label}; manual evidence={evidence.get(f'AC-{n:02d}','not supplied')}")
    def csv_check(path,required=None):
        if not path.is_file():return False,"file missing"
        with path.open(newline="",encoding="utf-8-sig") as fh:
            rows=list(csv.DictReader(fh))
        return (bool(rows) and (not required or set(required)<=set(rows[0]))),f"rows={len(rows)}; columns={list(rows[0]) if rows else []}"
    labels=OUT/"cluster_labels.csv"
    ok,detail=csv_check(labels)
    if ok:
        with labels.open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
        idcol=next((x for x in ("company_id","ticker","id") if x in rows[0]),None)
        cluster=next((x for x in ("cluster_id","cluster") if x in rows[0]),None)
        ok=bool(idcol and cluster and len(rows)==92 and len({r[idcol] for r in rows})==92 and all(r[cluster].strip() for r in rows))
    gate(15,ok,detail)
    pc=OUT/"pros_cons_generated.csv";ok,detail=csv_check(pc)
    if ok:
        with pc.open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
        idcol=next((x for x in ("company_id","ticker") if x in rows[0]),None)
        typecol=next((x for x in ("item_type","type","category") if x in rows[0]),None)
        groups={}
        if idcol and typecol:
            for row in rows:groups.setdefault(row[idcol],set()).add(row[typecol].strip().lower())
        ok=len(groups)==92 and all("pro" in v and "con" in v for v in groups.values())
    gate(16,ok,detail)
    pdfs=list((ROOT/"reports"/"tearsheets").glob("*.pdf"))
    gate(17,len(pdfs)==92 and all(p.stat().st_size>=30*1024 for p in pdfs),f"PDF count={len(pdfs)}, >=30KB={sum(p.stat().st_size>=30*1024 for p in pdfs)}")
    pytest_report=ROOT/"reports"/"pytest_report.html"
    gate(18,evidence.get("AC-18") is True and pytest_report.is_file(),"Requires actual pytest output >=60 collected, zero failed and generated HTML")
    valid=OUT/"validation_failures.csv"
    ok,detail=csv_check(valid,["company_id","field","issue","severity"])
    gate(19,ok,detail)
    guide=ROOT/"docs"/"analyst_guide.pdf"
    pages=None
    if guide.is_file():
        try:
            from pypdf import PdfReader
            pages=len(PdfReader(str(guide)).pages)
        except ImportError: pass
    gate(20,pages is not None and pages>=10,f"guide pages={pages}")
    OUT.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(results,indent=2),encoding="utf-8")
    passed=sum(x["status"]=="PASS" for x in results.values())
    print(f"Day 45: {passed}/20 PASS; {20-passed}/20 FAIL. Details: {REPORT}")
    return 0 if passed==20 else 1
if __name__=="__main__":raise SystemExit(main())
