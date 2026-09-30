"""Day 18 — peer-group percentile ranking engine."""
from __future__ import annotations
import argparse, os, re, sqlite3
from pathlib import Path
import pandas as pd

METRICS=("roe","roce","net_profit_margin","debt_to_equity","free_cash_flow","pat_cagr_5yr","revenue_cagr_5yr","eps_cagr_5yr","interest_coverage","asset_turnover")
METRIC_COLUMNS={m:m for m in METRICS}

def _norm_col(v): return re.sub(r"[^0-9a-z]+","_",str(v).strip().lower()).strip("_")
def _resolve_workbook(source):
    p=Path(source)
    if p.is_file(): return p
    hits=sorted(p.glob("*peer_groups*.xlsx"))
    if not hits: raise FileNotFoundError(f"No peer_groups.xlsx workbook found in {source}")
    if len(hits)>1: raise RuntimeError(f"Ambiguous peer_groups workbooks: {[x.name for x in hits]}")
    return hits[0]

def load_peer_memberships(source):
    df=pd.read_excel(_resolve_workbook(source))
    df.columns=[_norm_col(c) for c in df.columns]
    aliases={"group_name":"peer_group_name","peer_group":"peer_group_name","company":"company_id","peer_company":"peer_company_id","peer":"peer_company_id"}
    df=df.rename(columns={k:v for k,v in aliases.items() if k in df.columns})
    missing={"company_id","peer_group_name"}-set(df.columns)
    if missing: raise ValueError(f"peer_groups.xlsx missing required columns: {sorted(missing)}")
    rows=[]
    for _,r in df.iterrows():
        if pd.notna(r["company_id"]) and pd.notna(r["peer_group_name"]): rows.append((str(r["company_id"]).strip(),str(r["peer_group_name"]).strip()))
        if "peer_company_id" in df.columns and pd.notna(r["peer_company_id"]) and pd.notna(r["peer_group_name"]): rows.append((str(r["peer_company_id"]).strip(),str(r["peer_group_name"]).strip()))
    return pd.DataFrame(rows,columns=["company_id","peer_group_name"]).drop_duplicates().reset_index(drop=True)

def _query_metric_frame(con):
    sql="""SELECT fr.company_id,fr.year,fr.return_on_equity_pct AS roe,
    CASE WHEN (COALESCE(bs.equity_capital,0)+COALESCE(bs.reserves,0)+COALESCE(bs.borrowings,0))>0
    THEN pnl.operating_profit*100.0/(COALESCE(bs.equity_capital,0)+COALESCE(bs.reserves,0)+COALESCE(bs.borrowings,0)) END AS roce,
    fr.net_profit_margin_pct AS net_profit_margin,fr.debt_to_equity,fr.free_cash_flow_cr AS free_cash_flow,
    fr.pat_cagr_5yr,fr.revenue_cagr_5yr,fr.eps_cagr_5yr,fr.interest_coverage,fr.asset_turnover
    FROM financial_ratios fr LEFT JOIN profitandloss pnl ON pnl.company_id=fr.company_id AND pnl.year=fr.year
    LEFT JOIN balancesheet bs ON bs.company_id=fr.company_id AND bs.year=fr.year"""
    return pd.read_sql_query(sql,con)

def _percent_rank(values):
    valid=values.notna(); out=pd.Series(float("nan"),index=values.index); n=int(valid.sum())
    if n==0:return out
    if n==1: out.loc[valid]=0.0; return out
    ranks=values.loc[valid].rank(method="min",ascending=True)
    out.loc[valid]=(ranks-1)/(n-1); return out

def compute_peer_percentiles(metrics,memberships):
    known=set(metrics.company_id.astype(str))
    memberships=memberships.copy()
    if memberships.empty: return pd.DataFrame(columns=["company_id","peer_group_name","metric","value","percentile_rank","year"]),[f"{x}: No peer group assigned" for x in sorted(known)]
    memberships["company_id"]=memberships.company_id.astype(str)
    memberships=memberships[memberships.company_id.isin(known)].drop_duplicates()
    messages=[f"{x}: No peer group assigned" for x in sorted(known-set(memberships.company_id))]
    merged=metrics.merge(memberships,on="company_id",how="inner"); rows=[]
    for (group,year),frame in merged.groupby(["peer_group_name","year"],sort=True):
        for metric in METRICS:
            vals=pd.to_numeric(frame[metric],errors="coerce"); pct=_percent_rank(vals)
            if metric=="debt_to_equity": pct=1.0-pct
            for idx in frame.index[pct.notna()]:
                rows.append({"company_id":str(frame.loc[idx,"company_id"]),"peer_group_name":str(group),"metric":metric,"value":float(vals.loc[idx]),"percentile_rank":float(pct.loc[idx]),"year":int(year)})
    out=pd.DataFrame(rows,columns=["company_id","peer_group_name","metric","value","percentile_rank","year"])
    return out.drop_duplicates(["company_id","peer_group_name","metric","year"]).sort_values(["peer_group_name","year","metric","company_id"]).reset_index(drop=True),messages

def populate_peer_percentiles(db_path,peer_groups_source="data/raw"):
    memberships=load_peer_memberships(peer_groups_source); con=sqlite3.connect(db_path)
    try:
        output,messages=compute_peer_percentiles(_query_metric_frame(con),memberships)
        con.execute("DROP TABLE IF EXISTS peer_percentiles")
        con.execute("""CREATE TABLE peer_percentiles(id INTEGER PRIMARY KEY,company_id TEXT NOT NULL,peer_group_name TEXT NOT NULL,metric TEXT NOT NULL,value REAL,percentile_rank REAL,year INTEGER NOT NULL,FOREIGN KEY(company_id) REFERENCES companies(id),UNIQUE(company_id,peer_group_name,metric,year))""")
        if not output.empty: output.to_sql("peer_percentiles",con,if_exists="append",index=False)
        con.execute("CREATE INDEX idx_peer_percentiles_group_metric ON peer_percentiles(peer_group_name,metric,year)")
        con.commit()
        if con.execute("PRAGMA foreign_key_check").fetchall(): raise RuntimeError("Foreign-key violations after peer population")
    finally: con.close()
    return output,messages

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--db",default="db/nifty100.db"); p.add_argument("--peer-groups",default="data/raw"); a=p.parse_args()
    out,msg=populate_peer_percentiles(a.db,a.peer_groups)
