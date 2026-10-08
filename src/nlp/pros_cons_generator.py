"""Day 30: rule-based NLP pros/cons generator."""
from __future__ import annotations
import argparse, math, sqlite3
from pathlib import Path
import pandas as pd

THRESHOLD=60.0
PRO_TEXT={
"P01":"Consistently high return on equity above 20% demonstrates exceptional capital efficiency",
"P02":"Strong free cash flow generation over 5 years signals healthy business fundamentals",
"P03":"Debt-free balance sheet provides financial flexibility and eliminates interest burden",
"P04":"Revenue growing at above 15% CAGR over 5 years reflects strong business momentum",
"P05":"Operating profit margin above 25% indicates strong pricing power and cost discipline",
"P06":"Net profit compounding at above 20% over 5 years creates significant shareholder value",
"P07":"Very high interest coverage ratio reflects negligible financial stress from debt servicing",
"P08":"Consistent dividend yield above 2% backed by positive free cash flow",
"P09":"Earnings per share growing above 15% CAGR indicates strong earnings quality and compounding",
"P10":"Return on equity improving for 3 consecutive years shows strengthening business quality",
"P11":"Revenue growing slower than profits shows improving operating leverage and scale benefits",
"P12":"Growing asset base funded by internal accruals reflects self-sustaining growth",
}
CON_TEXT={
"C01":"Debt-to-equity ratio of {de:.2f} is elevated for a non-financial company and warrants monitoring",
"C02":"Free cash flow negative for 3 consecutive years raises concern about cash generation quality",
"C03":"Operating margins declining for 3 consecutive years suggest pricing or cost pressure",
"C04":"Company reported a net loss in the most recent financial year",
"C05":"Revenue contraction over 2 consecutive years indicates demand weakness or market share loss",
"C06":"Interest coverage ratio below 1.5x indicates the company is at risk of not meeting its debt obligations",
"C07":"Dividend payout ratio above 100% means the company is paying dividends from reserves, which is unsustainable",
"C08":"Rising debt-to-equity ratio over 3 years suggests increasing financial leverage risk",
"C09":"Earnings per share declining for 3 consecutive years reflects deteriorating profitability",
"C10":"Return on capital employed below 10% suggests the business is not generating sufficient returns on invested capital",
"C11":"Net debt exceeding 3 times EBITDA is a high leverage ratio and limits financial flexibility",
"C12":"Revenue growing at below 5% over 5 years lags inflation and suggests limited business momentum",
}
OUT_COLS=["company_id","type","rule_id","text","confidence_pct"]

def num(v):
    try:
        x=float(v); return x if math.isfinite(x) else None
    except (TypeError,ValueError): return None

def cols(con,table):
    return [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]

def pick(cs,*names):
    m={str(c).lower().replace("_",""):c for c in cs}
    for n in names:
        if n.lower().replace("_","") in m:return m[n.lower().replace("_","")]

def latest(df):
    if df.empty:return df
    df=df.copy(); df["_y"]=pd.to_numeric(df["year"],errors="coerce")
    return df.sort_values(["company_id","_y"]).drop_duplicates("company_id",keep="last").drop(columns="_y")

def read_table(con,table,fields):
    cs=cols(con,table); ic=pick(cs,"company_id","id","ticker"); yc=pick(cs,"year","metric_year","fy")
    if not ic:return pd.DataFrame(columns=["company_id","year",*fields])
    sel=[f'"{ic}" AS company_id',f'"{yc}" AS year' if yc else "NULL AS year"]
    for f in fields:
        c=pick(cs,f,f.replace("_pct",""),f.replace("_cr",""))
        sel.append(f'"{c}" AS "{f}"' if c else f'NULL AS "{f}"')
    return latest(pd.read_sql_query(f'SELECT {",".join(sel)} FROM "{table}"',con))

def history(con,cid):
    pnl=read_table(con,"profitandloss",["sales","operating_profit","opm_percentage","net_profit","eps","depreciation"])
    rat=read_table(con,"financial_ratios",["return_on_equity_pct","debt_to_equity","free_cash_flow_cr","interest_coverage","earnings_per_share","operating_profit_margin_pct","revenue_cagr_5yr","pat_cagr_5yr","eps_cagr_5yr","total_debt_cr"])
    bs=read_table(con,"balancesheet",["borrowings","total_assets"])
    cf=read_table(con,"cashflow",["cash_from_operating_activity"])
    frames=[]
    for d in (pnl,rat,bs,cf):
        d=d[d.company_id.astype(str)==str(cid)].copy()
        if not d.empty: frames.append(d)
    if not frames:return pd.DataFrame(columns=["year"])
    h=frames[0]
    for d in frames[1:]:h=h.merge(d,on=["company_id","year"],how="outer",suffixes=("","_x"))
    for c in ["sales","opm_percentage","operating_profit_margin_pct","return_on_equity_pct","debt_to_equity","free_cash_flow_cr","earnings_per_share","total_assets","borrowings","total_debt_cr"]:
        if c not in h:h[c]=pd.NA
    return h.sort_values("year").reset_index(drop=True)

def series_ok(h,c,pred,n):
    if c not in h:return False
    v=[num(x) for x in h[c].tolist()]; v=[x for x in v if x is not None]
    return len(v)>=n and all(pred(x) for x in v[-n:])

def trend_ok(h,c,n,direction):
    if c not in h:return False
    v=[num(x) for x in h[c].tolist()]; v=[x for x in v if x is not None]
    if len(v)<n:return False
    v=v[-n:]
    op=(lambda a,b:a>b) if direction=="up" else (lambda a,b:a<b)
    return all(op(v[i],v[i-1]) for i in range(1,len(v)))

def val(row,*names):
    for n in names:
        if n in row.index:
            x=num(row[n])
            if x is not None:return x

def conf(base,extra=0): return min(100.0,max(61.0,base+max(0,extra)))

def rules(row,h,financial):
    r=[]; roe=val(row,"return_on_equity_pct"); de=val(row,"debt_to_equity"); fcf=val(row,"free_cash_flow_cr")
    opm=val(row,"operating_profit_margin_pct","opm_percentage"); rev=val(row,"revenue_cagr_5yr")
    pat=val(row,"pat_cagr_5yr"); epsc=val(row,"eps_cagr_5yr"); icr=val(row,"interest_coverage")
    payout=val(row,"dividend_payout_ratio_pct"); roce=val(row,"roce_percentage"); np=val(row,"net_profit")
    dy=val(row,"dividend_yield","dividend_yield_pct"); borrow=val(row,"borrowings","total_debt_cr")
    sales=val(row,"sales"); cash=val(row,"cash_and_equivalents","cash")
    def add(t,rid,text,c): r.append({"type":t,"rule_id":rid,"text":text,"confidence_pct":c})
    if series_ok(h,"return_on_equity_pct",lambda x:x>20,3): add("pro","P01",PRO_TEXT["P01"],conf(72,(roe or 20)-20))
    if series_ok(h,"free_cash_flow_cr",lambda x:x>0,5): add("pro","P02",PRO_TEXT["P02"],75)
    if de is not None and abs(de)<1e-12:add("pro","P03",PRO_TEXT["P03"],95)
    if rev is not None and rev>15:add("pro","P04",PRO_TEXT["P04"],conf(72,rev-15))
    if opm is not None and opm>25:add("pro","P05",PRO_TEXT["P05"],conf(72,opm-25))
    if pat is not None and pat>20:add("pro","P06",PRO_TEXT["P06"],conf(72,pat-20))
    if (icr is not None and icr>10) or (de is not None and abs(de)<1e-12):add("pro","P07",PRO_TEXT["P07"],95)
    if dy is not None and dy>2 and fcf is not None and fcf>0:add("pro","P08",PRO_TEXT["P08"],85)
    if epsc is not None and epsc>15:add("pro","P09",PRO_TEXT["P09"],conf(72,epsc-15))
    if trend_ok(h,"return_on_equity_pct",3,"up"):add("pro","P10",PRO_TEXT["P10"],82)
    if rev is not None and pat is not None and rev>pat:add("pro","P11",PRO_TEXT["P11"],conf(68,rev-pat))
    debtc="borrowings" if "borrowings" in h else "total_debt_cr"
    if len(h)>=2 and trend_ok(h,"total_assets",2,"up") and trend_ok(h,debtc,2,"down"):add("pro","P12",PRO_TEXT["P12"],82)
    if not financial and de is not None and de>2:add("con","C01",CON_TEXT["C01"].format(de=de),conf(72,(de-2)*8))
    if series_ok(h,"free_cash_flow_cr",lambda x:x<0,3):add("con","C02",CON_TEXT["C02"],82)
    opmc="operating_profit_margin_pct" if "operating_profit_margin_pct" in h else "opm_percentage"
    if trend_ok(h,opmc,3,"down"):add("con","C03",CON_TEXT["C03"],82)
    if np is not None and np<0:add("con","C04",CON_TEXT["C04"],90)
    if trend_ok(h,"sales",2,"down"):add("con","C05",CON_TEXT["C05"],82)
    if icr is not None and icr<1.5:add("con","C06",CON_TEXT["C06"],conf(75,(1.5-icr)*10))
    if payout is not None and payout>100:add("con","C07",CON_TEXT["C07"],conf(75,payout-100))
    if trend_ok(h,"debt_to_equity",3,"up"):add("con","C08",CON_TEXT["C08"],82)
    if trend_ok(h,"earnings_per_share",3,"down"):add("con","C09",CON_TEXT["C09"],82)
    if roce is not None and roce<10:add("con","C10",CON_TEXT["C10"],conf(75,(10-roce)*3))
    dep=val(row,"depreciation") or 0
    ebitda=(val(row,"operating_profit") or ((sales or 0)*(opm or 0)/100))+dep
    netdebt=(borrow or 0)-(cash or 0)
    if ebitda>0 and netdebt>3*ebitda:add("con","C11",CON_TEXT["C11"],conf(78,(netdebt/ebitda-3)*5))
    if rev is not None and rev<5:add("con","C12",CON_TEXT["C12"],conf(75,(5-rev)*3))
    return r

def generate(db_path:Path,output:Path,strict=True):
    if not db_path.exists():raise FileNotFoundError(db_path)
    con=sqlite3.connect(db_path)
    try:
        companies=pd.read_sql_query("SELECT * FROM companies",con)
        if companies.empty:raise ValueError("companies table is empty")
        rows=[]
        for _,c in companies.iterrows():
            cid=str(c.get("id") or c.get("company_id") or c.get("ticker"))
            h=history(con,cid); row=c.copy()
            if not h.empty:
                latest_row=h.iloc[-1]
                for k,v in latest_row.items():
                    if k!="year":row[k]=v
            rr=read_table(con,"financial_ratios",["return_on_equity_pct","operating_profit_margin_pct","debt_to_equity","interest_coverage","free_cash_flow_cr","earnings_per_share","dividend_payout_ratio_pct","revenue_cagr_5yr","pat_cagr_5yr","eps_cagr_5yr","total_debt_cr"])
            rr=rr[rr.company_id.astype(str)==cid]
            if not rr.empty:
                for k,v in rr.iloc[-1].items():
                    if k not in ("company_id","year"):row[k]=v
            fin="financial" in str(row.get("sector","")).lower()
            for x in rules(row,h,fin):
                if x["confidence_pct"]>THRESHOLD:rows.append({"company_id":cid,**x})
        out=pd.DataFrame(rows,columns=OUT_COLS); output.parent.mkdir(parents=True,exist_ok=True); out.to_csv(output,index=False)
        coverage=out.groupby(["company_id","type"]).size().unstack(fill_value=0) if not out.empty else pd.DataFrame()
        missing=[]
        for cid in companies["id"].astype(str):
            if coverage.empty or coverage.get("pro",pd.Series(dtype=int)).get(cid,0)<1:missing.append((cid,"pro"))
            if coverage.empty or coverage.get("con",pd.Series(dtype=int)).get(cid,0)<1:missing.append((cid,"con"))
        if strict and missing:raise ValueError(f"Coverage validation failed for {len(missing)} company/type combinations: {missing[:10]}")
        return out
    finally:con.close()

def main():
    p=argparse.ArgumentParser();p.add_argument("--db",type=Path,default=Path("db/nifty100.db"));p.add_argument("--output",type=Path,default=Path("output/pros_cons_generated.csv"));p.add_argument("--allow-incomplete-coverage",action="store_true");a=p.parse_args()
    out=generate(a.db,a.output,strict=not a.allow_incomplete_coverage)
    print(f"generated rows: {len(out)}");print(f"companies: {out.company_id.nunique() if not out.empty else 0}");print(f"pros: {(out.type=='pro').sum() if not out.empty else 0}");print(f"cons: {(out.type=='con').sum() if not out.empty else 0}")
if __name__=="__main__":main()
