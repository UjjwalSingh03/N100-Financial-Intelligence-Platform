"""Day 33: two-page ReportLab company tearsheet. Run: python -m src.reports.tearsheet --db db/nifty100.db --ticker TCS"""
from __future__ import annotations
import argparse
import csv
import sqlite3
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

NAVY = colors.HexColor("#122744")
GREEN = colors.HexColor("#17834B")
RED = colors.HexColor("#B33A42")
MUTED = colors.HexColor("#5B6878")
PAGE_W, PAGE_H = 595.28, 841.89
MARGIN = 38
WIDTH = PAGE_W - 2 * MARGIN
STYLE = ParagraphStyle("wrap", fontName="Helvetica", fontSize=8, leading=11, wordWrap="CJK")
PATTERNS = ("Reinvestor", "Shareholder Returns", "Liquidating Assets", "Distress Signal",
            "Growth Funded by Debt", "Cash Accumulator", "Pre-Revenue", "Mixed")


def _rows(con, table, ticker):
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
        return []
    order = "year" if table != "prosandcons" else "id"
    return [dict(r) for r in con.execute(f'SELECT * FROM "{table}" WHERE company_id=? ORDER BY {order}', (ticker,))]


def _num(v):
    try:
        return float(v) if v is not None else None
    except (ValueError, TypeError):
        return None


def _fmt(v, suffix=""):
    n = _num(v)
    return f"{n:,.1f}{suffix}" if n is not None else "N/A"


def _latest(rows):
    return rows[-1] if rows else {}


def _panel(c, x, top, w, h, title):
    y = top - h
    c.setStrokeColor(colors.HexColor("#D9E2EB"))
    c.roundRect(x, y, w, h, 7, stroke=1, fill=0)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x + 10, top - 17, title)
    return y


def _bars(c, x, top, w, h, title, rows, key, color):
    y = _panel(c, x, top, w, h, title)
    values = [(str(r["year"]), _num(r.get(key))) for r in rows[-10:]]
    values = [(yr, val) for yr, val in values if val is not None]
    if not values:
        c.setFillColor(MUTED); c.drawString(x + 12, y + h / 2, "No data available"); return
    baseline = y + 28
    max_abs = max(abs(v) for _, v in values) or 1
    space = (w - 26) / len(values)
    for i, (yr, val) in enumerate(values):
        bh = abs(val) / max_abs * (h - 68)
        bx = x + 13 + i * space + space * .17
        c.setFillColor(color if val >= 0 else RED)
        c.rect(bx, baseline if val >= 0 else baseline - bh, space * .65, bh, fill=1, stroke=0)
        c.saveState(); c.translate(bx + 2, y + 7); c.rotate(55)
        c.setFillColor(MUTED); c.setFont("Helvetica", 6); c.drawString(0, 0, yr[-2:]); c.restoreState()


def _line_chart(c, x, top, w, h, rows):
    y = _panel(c, x, top, w, h, "ROE / ROCE (%)")
    years = sorted({int(r["year"]) for r in rows})[-10:]
    if not years:
        c.setFillColor(MUTED); c.drawString(x + 12, y + 55, "No ratio data"); return
    for key, color, offset in (("return_on_equity_pct", GREEN, 0), ("roce_percentage", RED, 1)):
        vals = [(yr, _num(next((r.get(key) for r in rows if int(r["year"]) == yr), None))) for yr in years]
        valid = [(yr, v) for yr, v in vals if v is not None]
        if not valid: continue
        lo = min(0, min(v for _, v in valid)); hi = max(1, max(v for _, v in valid))
        c.setStrokeColor(color); c.setLineWidth(1.6)
        prev = None
        for yr, v in vals:
            if v is None: prev = None; continue
            px = x + 30 + (years.index(yr) / max(1, len(years)-1)) * (w-60)
            py = y + 25 + (v-lo) / max(1, hi-lo) * (h-57)
            if prev: c.line(*prev, px, py)
            prev = (px, py)
        c.setFillColor(color); c.setFont("Helvetica", 7)
        c.drawString(x + 12 + offset * 95, top - 31, "ROE" if offset == 0 else "ROCE")


def _table(c, x, top, w, heading, headers, rows, heights=None):
    c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 10); c.drawString(x, top, heading)
    cells = [[Paragraph(escape(str(z)), STYLE) for z in headers]]
    cells += [[Paragraph(escape(str(z)), STYLE) for z in row] for row in rows]
    t = Table(cells, colWidths=[w / len(headers)] * len(headers), repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([("WORDWRAP", (0,0), (-1,-1), "CJK"),
                           ("BACKGROUND",(0,0),(-1,0),NAVY), ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                           ("VALIGN",(0,0),(-1,-1),"TOP"), ("BOTTOMPADDING",(0,0),(-1,-1),5),
                           ("TOPPADDING",(0,0),(-1,-1),5), ("LINEBELOW",(0,0),(-1,-1),.3,colors.lightgrey)]))
    _, height = t.wrap(w, 1000)
    if height > top - 45: raise ValueError(f"{heading} overflows page")
    t.drawOn(c, x, top - 7 - height)
    return top - 7 - height


def _bullets(c, x, top, w, title, items, color, limit=4):
    c.setFillColor(color); c.setFont("Helvetica-Bold", 10); c.drawString(x, top, title)
    y = top - 15
    for item in items[:limit]:
        p = Paragraph(escape(str(item)), STYLE)
        _, ph = p.wrap(w - 18, 100)
        if y - ph - 5 < 65: raise ValueError(f"{title} overflows page")
        c.setFillColor(color); c.circle(x + 4, y - 5, 2, fill=1, stroke=0)
        p.drawOn(c, x + 13, y - ph)
        y -= ph + 6
    if not items:
        c.setFillColor(MUTED); c.setFont("Helvetica", 8); c.drawString(x + 10, y - 5, "No source notes available")
        y -= 15
    return y


def _stacked_balance(c, x, top, w, h, rows):
    y = _panel(c, x, top, w, h, "Balance Sheet Composition — 10 Years")
    series = []
    for r in rows[-10:]:
        eq = (_num(r.get("equity_capital")) or 0) + (_num(r.get("reserves")) or 0)
        series.append((str(r["year"]), [max(0,eq), max(0,_num(r.get("borrowings")) or 0),
                                         max(0,_num(r.get("other_liabilities")) or 0)]))
    scale = max([sum(v) for _,v in series] or [1]) or 1
    for i,(yr,values) in enumerate(series):
        bx=x+13+i*(w-26)/max(1,len(series)); by=y+20
        for value,color in zip(values,(GREEN,colors.HexColor("#4775AD"),colors.HexColor("#C3A36A"))):
            bh=value/scale*(h-52); c.setFillColor(color); c.rect(bx,by,(w-26)/max(1,len(series))*.65,bh,stroke=0,fill=1); by+=bh
        c.setFillColor(MUTED); c.setFont("Helvetica",6); c.drawString(bx,y+8,yr[-2:])


def _waterfall(c, x, top, w, h, cf):
    y = _panel(c, x, top, w, h, "Cash Flow Waterfall — Latest Year")
    keys = [("CFO", "cash_from_operating_activity"), ("CFI", "cash_from_investing_activity"),
            ("CFF", "cash_from_financing_activity"), ("Net", "net_cash_flow")]
    vals = [_num(cf.get(k)) for _, k in keys]
    if vals[3] is None and all(v is not None for v in vals[:3]): vals[3] = sum(vals[:3])
    if any(v is None for v in vals):
        c.setFillColor(MUTED); c.drawString(x+12, y+60, "Incomplete cash flow data"); return
    bounds = [0]; running = 0
    for v in vals[:3]: running += v; bounds.append(running)
    span = max(bounds + [vals[3]]) - min(bounds + [vals[3]])
    lo = min(bounds + [vals[3]], default=0)
    scale = (h-65) / (span or 1)
    def yy(v): return y + 30 + (v-lo)*scale
    bw = (w-36)/4
    running = 0
    for i, (label, _) in enumerate(keys):
        v = vals[i]
        start, end = (running, running+v) if i < 3 else (0, v)
        if i < 3: running = end
        c.setFillColor(GREEN if v >= 0 else RED)
        c.rect(x+18+i*bw, min(yy(start), yy(end)), bw*.62, max(1,abs(yy(end)-yy(start))), stroke=0, fill=1)
        c.setFillColor(MUTED); c.setFont("Helvetica", 7); c.drawCentredString(x+18+i*bw+bw*.31,y+12,label)


def generate(db_path, ticker, output_path, capital_csv="output/capital_allocation.csv"):
    output_path = Path(output_path); output_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        company = con.execute("SELECT * FROM companies WHERE id=? OR ticker=? LIMIT 1", (ticker,ticker)).fetchone()
        if company is None: raise ValueError(f"Unknown company: {ticker}")
        company = dict(company); ticker = company["id"]
        pnl = _rows(con,"profitandloss",ticker); bs = _rows(con,"balancesheet",ticker)
        cf = _rows(con,"cashflow",ticker); ratios = _rows(con,"financial_ratios",ticker)
        notes = _rows(con,"prosandcons",ticker)
    allocation = "N/A"
    path = Path(capital_csv)
    if path.exists():
        with path.open(encoding="utf-8", newline="") as f:
            matches = [r for r in csv.DictReader(f) if r.get("company_id")==ticker and str(r.get("year","")).isdigit()]
        if matches: allocation = max(matches,key=lambda r:int(r["year"]))["pattern_label"]
    if allocation not in PATTERNS: allocation = "N/A"
    latest_p, latest_b, latest_c, latest_r = map(_latest,(pnl,bs,cf,ratios))
    c = canvas.Canvas(str(output_path), pagesize=(PAGE_W,PAGE_H))
    c.setFillColor(NAVY); c.rect(0,PAGE_H-92,PAGE_W,92,fill=1,stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold",17)
    title = str(company.get("company_name") or ticker)
    while stringWidth(title,"Helvetica-Bold",17)>WIDTH: title=title[:-2]
    c.drawString(MARGIN,PAGE_H-49,title)
    c.setFont("Helvetica",10); c.drawString(MARGIN,PAGE_H-68,f"{ticker}  |  {company.get('sector') or 'Unknown Sector'}")
    kpis = [("Revenue",latest_p.get("sales"),""),("Net Profit",latest_p.get("net_profit"),""),
            ("OPM",latest_p.get("opm_percentage"),"%"),("ROE",latest_r.get("return_on_equity_pct"),"%"),
            ("Debt / Equity",latest_r.get("debt_to_equity"),"x"),("EPS",latest_p.get("eps"),"")]
    tile_w=(WIDTH-20)/3
    for i,(name,value,suffix) in enumerate(kpis):
        x=MARGIN+(i%3)*(tile_w+10); top=PAGE_H-112-(i//3)*75
        _panel(c,x,top,tile_w,65,name)
        c.setFillColor(NAVY); c.setFont("Helvetica-Bold",15); c.drawString(x+10,top-44,_fmt(value,suffix))
    top=PAGE_H-282
    _bars(c,MARGIN,top,(WIDTH-12)/2,190,"Revenue — 10 Years",pnl,"sales",colors.HexColor("#2B76AD"))
    _bars(c,MARGIN+(WIDTH+12)/2,top,(WIDTH-12)/2,190,"Net Profit — 10 Years",pnl,"net_profit",GREEN)
    _line_chart(c,MARGIN,top-205,WIDTH,190,ratios)
    c.setFillColor(MUTED); c.setFont("Helvetica",8); c.drawString(MARGIN,30,"N100 Financial Intelligence Platform  •  Page 1 / 2")
    c.showPage()
    c.setFillColor(NAVY); c.rect(0,PAGE_H-58,PAGE_W,58,fill=1,stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold",14); c.drawString(MARGIN,PAGE_H-36,f"{ticker}  |  Financial Position & Signals")
    # Compact stacked composition bars with a wrapped annual-value table below.\n    _stacked_balance(c, MARGIN, PAGE_H-79, WIDTH, 104, bs)
    b_rows=[]
    for r in bs[-10:]:
        equity=(_num(r.get("equity_capital")) or 0)+(_num(r.get("reserves")) or 0)
        b_rows.append((r["year"],_fmt(equity),_fmt(r.get("borrowings")),_fmt(r.get("other_liabilities"))))
    y=_table(c,MARGIN,PAGE_H-192,WIDTH,"Balance Sheet Composition — Annual Values",
             ("Year","Equity + Reserves","Borrowings","Other Liabilities"),b_rows)
    _waterfall(c,MARGIN,y-16,WIDTH,135,latest_c)
    y=y-168
    pros=[r.get("description","") for r in notes if str(r.get("item_type","")).lower().startswith("pro")]
    cons=[r.get("description","") for r in notes if str(r.get("item_type","")).lower().startswith("con")]
    left=_bullets(c,MARGIN,y,(WIDTH-14)/2,"Pros",pros,GREEN)
    right=_bullets(c,MARGIN+(WIDTH+14)/2,y,(WIDTH-14)/2,"Cons",cons,RED)
    bottom=min(left,right)
    if bottom < 73: raise ValueError("Page 2 notes overflow")
    c.setFillColor(NAVY); c.roundRect(MARGIN,36,WIDTH,29,6,fill=1,stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold",9)
    c.drawString(MARGIN+10,46,f"CAPITAL ALLOCATION  |  {allocation}")
    c.setFillColor(MUTED); c.setFont("Helvetica",8); c.drawString(MARGIN,22,"N100 Financial Intelligence Platform  •  Page 2 / 2")
    c.showPage(); c.save()
    return output_path


def main():
    p=argparse.ArgumentParser(); p.add_argument("--db",default="db/nifty100.db")
    p.add_argument("--ticker",required=True); p.add_argument("--output",default=None)
    p.add_argument("--capital-csv",default="output/capital_allocation.csv")
    a=p.parse_args()
    result=generate(a.db,a.ticker,a.output or f"output/tearsheets/{a.ticker}.pdf",a.capital_csv)
    print(result)


if __name__=="__main__": main()
