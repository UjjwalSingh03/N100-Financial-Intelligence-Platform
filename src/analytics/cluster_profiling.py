"""Day 37: cluster profiles, Pearson heatmap, sector outliers and portfolio statistics."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from src.analytics.clustering import FEATURES, load_features, impute_features, _latest, _fcf_cagr
import sqlite3

KPIS = (*FEATURES, "sales", "net_profit", "eps", "cash_from_operating_activity", "free_cash_flow_cr")
NAMES = ("High-Quality Compounders", "Defensive Dividend Payers", "Value Cyclicals",
         "Distressed or Turnaround", "Emerging Growth")


def load_kpis(db):
    base = load_features(db)
    with sqlite3.connect(db) as con:
        pl = pd.read_sql_query("SELECT * FROM profitandloss", con)
        cf = pd.read_sql_query("SELECT * FROM cashflow", con)
        ratios = pd.read_sql_query("SELECT * FROM financial_ratios", con)
    if not pl.empty:
        p = _latest(pl)
        cols = [x for x in ("sales", "net_profit", "eps") if x in p]
        base = base.merge(p[["company_id", *cols]], on="company_id", how="left", validate="one_to_one")
    if not cf.empty:
        c = _latest(cf)
        cols = [x for x in ("cash_from_operating_activity", "cash_from_investing_activity") if x in c]
        base = base.merge(c[["company_id", *cols]], on="company_id", how="left", validate="one_to_one")
    if not ratios.empty and "free_cash_flow_cr" in ratios:
        r = _latest(ratios)[["company_id", "free_cash_flow_cr"]]
        base = base.merge(r, on="company_id", how="left", validate="one_to_one")
    if "free_cash_flow_cr" not in base: base["free_cash_flow_cr"] = np.nan
    if {"cash_from_operating_activity", "cash_from_investing_activity"} <= set(base):
        derived = pd.to_numeric(base["cash_from_operating_activity"], errors="coerce") + pd.to_numeric(base["cash_from_investing_activity"], errors="coerce")
        base["free_cash_flow_cr"] = pd.to_numeric(base["free_cash_flow_cr"], errors="coerce").fillna(derived)
    for k in KPIS:
        if k not in base: base[k] = np.nan
        base[k] = pd.to_numeric(base[k], errors="coerce").replace([np.inf,-np.inf],np.nan)
    return base


def run(db="db/nifty100.db", labels_path="output/cluster_labels.csv",
        output_dir="output", report_dir="reports", expected=92):
    output_dir=Path(output_dir); report_dir=Path(report_dir)
    output_dir.mkdir(parents=True,exist_ok=True);report_dir.mkdir(parents=True,exist_ok=True)
    frame=load_kpis(db)
    labels=pd.read_csv(labels_path)
    required={"company_id","cluster_id"}
    if not required <= set(labels): raise ValueError("Day 36 cluster labels missing required columns")
    if labels.company_id.duplicated().any(): raise ValueError("Duplicate cluster assignments")
    if len(frame)!=expected or len(labels)!=expected: raise ValueError(f"Expected {expected} companies in both data and labels")
    frame=frame.merge(labels[["company_id","cluster_id"]],on="company_id",how="left",validate="one_to_one")
    if frame.cluster_id.isna().any() or set(frame.cluster_id.astype(int)) != set(range(5)):
        raise ValueError("Missing company assignment or missing cluster")
    # Use observed values for interpretable profiles; imputed values are exported separately.
    filled=impute_features(frame)
    profiles=[]
    for cluster, group in frame.groupby("cluster_id"):
        for feature in FEATURES:
            profiles.append({"cluster_id":int(cluster),"feature":feature,"mean":group[feature].mean(),
                             "median":group[feature].median(),"observed_count":int(group[feature].notna().sum()),
                             "imputed_mean":filled.loc[group.index,feature].mean()})
    pd.DataFrame(profiles).to_csv(output_dir/"cluster_profiles.csv",index=False)
    members=frame.groupby("cluster_id")["company_id"].apply(lambda x:", ".join(sorted(x))).reset_index(name="members")
    members.to_csv(output_dir/"cluster_members.csv",index=False)
    # Suggested names are provisional; team lead must review actual member lists.
    suggested=dict(zip(sorted(frame.cluster_id.unique().astype(int)),NAMES))
    pd.DataFrame([{"cluster_id":k,"suggested_name":v,"review_status":"PENDING TEAM LEAD REVIEW"}
                  for k,v in suggested.items()]).to_csv(output_dir/"cluster_name_review.csv",index=False)
    # Pearson pairwise-complete observations; missing values are not silently imputed for correlation.
    corr=frame[list(KPIS)].corr(method="pearson")
    corr.to_csv(output_dir/"correlation_matrix.csv")
    fig,ax=plt.subplots(figsize=(13,10))
    sns.heatmap(corr,annot=True,fmt=".2f",cmap="coolwarm",vmin=-1,vmax=1,center=0,
                linewidths=.5,ax=ax)
    ax.set_title("Latest available annual KPIs — Pearson correlation (N100)")
    fig.tight_layout();fig.savefig(report_dir/"correlation_heatmap.png",dpi=170);plt.close(fig)
    # Population z-scores within broad sector; zero variance / fewer than 2 values are not flagged.
    outliers=[]
    for sector,group in frame.groupby("sector",dropna=False):
        for k in KPIS:
            values=group[k].dropna()
            if len(values)<2:continue
            sd=values.std(ddof=0)
            if pd.isna(sd) or sd==0:continue
            mean=values.mean()
            for idx,value in values.items():
                z=(value-mean)/sd
                if abs(z)>3:
                    outliers.append({"company_id":frame.at[idx,"company_id"],"broad_sector":sector,
                                     "metric":k,"value":value,"sector_mean":mean,"sector_std":sd,"z_score":z})
    pd.DataFrame(outliers,columns=["company_id","broad_sector","metric","value","sector_mean","sector_std","z_score"]).to_csv(output_dir/"outlier_report.csv",index=False)
    stats=[]
    for k in KPIS:
        x=frame[k].dropna()
        stats.append({"kpi":k,"count":len(x),"P10":x.quantile(.10),"P25":x.quantile(.25),
                      "P50":x.quantile(.50),"P75":x.quantile(.75),"P90":x.quantile(.90),
                      "Mean":x.mean(),"Std":x.std(ddof=0)})
    pd.DataFrame(stats).to_csv(output_dir/"portfolio_stats.csv",index=False)
    print(f"Day 37: {len(frame)} companies; {len(outliers)} sector-metric outlier flags; cluster names pending team-lead review")
    return frame


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",default="db/nifty100.db");p.add_argument("--labels",default="output/cluster_labels.csv")
    p.add_argument("--output-dir",default="output");p.add_argument("--report-dir",default="reports")
    a=p.parse_args();run(a.db,a.labels,a.output_dir,a.report_dir)
