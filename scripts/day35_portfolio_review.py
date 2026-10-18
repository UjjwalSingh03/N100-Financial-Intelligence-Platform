"""Day 35: alphabetical, one-page-per-company portfolio PDF and Sprint 5 gate audit."""
from __future__ import annotations
import argparse
import csv
import sqlite3
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from scripts.day34_batch_reports import normalized_copy

METRICS = (
    ("Revenue", "profitandloss", "sales", True),
    ("Net Profit", "profitandloss", "net_profit", True),
    ("OPM %", "profitandloss", "opm_percentage", True),
    ("ROE %", "financial_ratios", "return_on_equity_pct", True),
    ("Debt / Equity", "financial_ratios", "debt_to_equity", False),
    ("EPS", "profitandloss", "eps", True),
)
NAVY=colors.HexColor("#122744")
STYLE=ParagraphStyle("portfolio",fontName="Helvetica",fontSize=10,leading=14,wordWrap="CJK")
TITLE=ParagraphStyle("title",parent=STYLE,fontName="Helvetica-Bold",fontSize=18,leading=23,textColor=NAVY)


def trend(current, previous, higher_is_better=True):
    """Return direction based on relative change; values within 2% are flat."""
    if current is None or previous is None: return "N/A"
    current,previous=float(current),float(previous)
    change=(current-previous)/max(abs(previous),1e-9)
    if abs(change)<=0.02: return "→"
    improved=change>0 if higher_is_better else change<0
    return "↑" if improved else "↓"


def build(db_path="db/nifty100.db", output="reports/portfolio/portfolio_summary.pdf"):
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        normalized=Path(temp)/"normalized.db"
        normalized_copy(db_path,normalized)
        with sqlite3.connect(normalized) as con:
            con.row_factory=sqlite3.Row
            companies=[dict(r) for r in con.execute("SELECT * FROM companies ORDER BY id COLLATE NOCASE")]
            if not companies: raise ValueError("No companies found")
            story=[]
            for index,company in enumerate(companies):
                if index: story.append(PageBreak())
                ticker=company["id"]
                story.extend([Paragraph(escape(str(company["company_name"] or ticker)),TITLE),
                              Spacer(1,7),Paragraph(escape(f"Ticker: {ticker}  |  Sector: {company['sector'] or 'Unknown'}"),STYLE),
                              Spacer(1,23),Paragraph("Six key performance indicators",STYLE),Spacer(1,10)])
                rows=[]
                for label,table,column,higher in METRICS:
                    values=[r[0] for r in con.execute(
                        f"SELECT {column} FROM {table} WHERE company_id=? AND {column} IS NOT NULL ORDER BY year DESC LIMIT 2",(ticker,))]
                    current=values[0] if values else None
                    previous=values[1] if len(values)>1 else None
                    direction=trend(current,previous,higher)
                    # ReportLab standard Helvetica lacks Unicode arrows: use ASCII equivalents in the PDF.
                    symbol={"↑":"UP","↓":"DOWN","→":"FLAT"}.get(direction,direction)
                    rows.append([label, f"{current:,.2f}" if current is not None else "N/A",symbol])
                table=Table([[ "KPI","Latest value","YoY trend"],*rows],colWidths=[225,165,130],repeatRows=1)
                table.setStyle(TableStyle([("WORDWRAP",(0,0),(-1,-1),"CJK"),("BACKGROUND",(0,0),(-1,0),NAVY),
                     ("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.4,colors.lightgrey),
                     ("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),10),
                     ("BOTTOMPADDING",(0,0),(-1,-1),10)]))
                story.extend([table,Spacer(1,16),Paragraph("UP = improved | DOWN = declined | FLAT = change within 2% | N/A = insufficient history.",STYLE)])
    doc=SimpleDocTemplate(str(output),pagesize=(595.28,841.89),leftMargin=37,rightMargin=37,topMargin=42,bottomMargin=42)
    doc.build(story)
    return output,len(companies)


def audit(root=".", expected_companies=92, expected_sectors=11):
    import pandas as pd
    from pypdf import PdfReader
    root=Path(root);output=root/"output";reports=root/"reports"
    checks=[]
    def record(name,ok,detail): checks.append({"check":name,"passed":bool(ok),"detail":str(detail)})
    pros=output/"pros_cons_generated.csv"
    if pros.exists():
        df=pd.read_csv(pros)
        idcol="company_id";typecol="type"
        valid={str(cid) for cid,g in df.groupby(idcol) if {"pro","con"}<=set(g[typecol].astype(str).str.lower())}
        record("pros_and_cons_coverage",len(valid)==expected_companies,f"{len(valid)} companies with both")
    else:record("pros_and_cons_coverage",False,"Missing CSV")
    record("analysis_parsed_exists",(output/"analysis_parsed.csv").exists(),"Structured analysis CSV")
    workbook=output/"cashflow_intelligence.xlsx"
    if workbook.exists():
        df=pd.read_excel(workbook,sheet_name="Cash Flow Intelligence")
        required={"company_id","cfo_quality_score","capex_intensity_pct","distress_flag"}
        record("cashflow_workbook",len(df)==expected_companies and required<=set(df.columns),
               f"{len(df)} rows; missing columns: {sorted(required-set(df.columns))}")
    else:record("cashflow_workbook",False,"Missing XLSX")
    record("distress_alerts_exists",(output/"distress_alerts.csv").exists(),"Distress CSV")
    pdfs=list((reports/"tearsheets").glob("*_tearsheet.pdf"))
    small=[p.name for p in pdfs if p.stat().st_size<30*1024]
    invalid=[]
    for p in pdfs:
        try:
            if len(PdfReader(str(p)).pages)!=2:invalid.append(p.name)
        except Exception:invalid.append(p.name)
    record("tearsheets",len(pdfs)==expected_companies and not small and not invalid,
           f"count={len(pdfs)}, under_30KB={small}, invalid_page_count={invalid}")
    sector=list((reports/"sector").glob("*_report.pdf"))
    record("sector_reports",len(sector)==expected_sectors,f"{len(sector)} sector PDFs")
    portfolio=reports/"portfolio"/"portfolio_summary.pdf"
    if portfolio.exists():
        try: count=len(PdfReader(str(portfolio)).pages)
        except Exception: count=-1
        record("portfolio_pages",count==expected_companies,f"{count} pages")
    else:record("portfolio_pages",False,"Missing portfolio PDF")
    result=output/"sprint5_exit_audit.csv";result.parent.mkdir(parents=True,exist_ok=True)
    with result.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["check","passed","detail"]);w.writeheader();w.writerows(checks)
    return result,checks


def main():
    p=argparse.ArgumentParser();p.add_argument("--db",default="db/nifty100.db")
    p.add_argument("--output",default="reports/portfolio/portfolio_summary.pdf")
    p.add_argument("--audit-only",action="store_true");a=p.parse_args()
    if not a.audit_only:
        path,n=build(a.db,a.output);print(f"Portfolio: {path} ({n} pages)")
    path,checks=audit();print(f"Audit: {path}; passed {sum(x['passed'] for x in checks)}/{len(checks)}")
    for c in checks:print(f"{'PASS' if c['passed'] else 'FAIL'} {c['check']}: {c['detail']}")


if __name__=="__main__":main()
