"""Sprint 6 Day 36: reproducible five-archetype clustering.

Run: python -m src.analytics.clustering --db db/nifty100.db
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

FEATURES = ("return_on_equity_pct", "debt_to_equity", "revenue_cagr_5yr",
            "fcf_cagr_5yr", "operating_profit_margin_pct")
ARCHETYPES = ("Quality Compounders", "Growth Leaders", "Cash Generators",
              "Leveraged Operators", "Turnaround / Challenged")


def _table(con, name):
    exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return pd.read_sql_query(f'SELECT * FROM "{name}"', con) if exists else pd.DataFrame()


def _latest(df):
    if df.empty:
        return df
    df = df.copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    return df.dropna(subset=["year"]).sort_values(["company_id", "year"]).drop_duplicates("company_id", keep="last")


def _fcf_cagr(cf, years=5):
    if cf.empty:
        return pd.DataFrame(columns=["company_id", "fcf_cagr_5yr"])
    cf = cf.copy()
    cf["year"] = pd.to_numeric(cf["year"], errors="coerce")
    cfo = pd.to_numeric(cf.get("cash_from_operating_activity"), errors="coerce")
    cfi = pd.to_numeric(cf.get("cash_from_investing_activity"), errors="coerce")
    cf["fcf"] = cfo + cfi
    result = []
    for company, group in cf.dropna(subset=["year", "fcf"]).groupby("company_id"):
        group = group.sort_values("year").drop_duplicates("year", keep="last")
        if group.empty:
            continue
        end = group.iloc[-1]
        earlier = group[group["year"] <= end["year"] - years]
        earlier = earlier[earlier["fcf"] > 0]
        growth = np.nan
        if not earlier.empty and end["fcf"] > 0:
            start = earlier.iloc[-1]
            elapsed = end["year"] - start["year"]
            growth = ((end["fcf"] / start["fcf"]) ** (1 / elapsed) - 1) * 100
        result.append({"company_id": company, "fcf_cagr_5yr": growth})
    return pd.DataFrame(result, columns=["company_id", "fcf_cagr_5yr"])


def load_features(db_path):
    with sqlite3.connect(db_path) as con:
        companies = _table(con, "companies")
        ratios = _table(con, "financial_ratios")
        pnl = _table(con, "profitandloss")
        cf = _table(con, "cashflow")
        sectors = _table(con, "sectors")
    if companies.empty or "id" not in companies:
        raise ValueError("A populated companies table with id is required")
    if companies["id"].duplicated().any():
        raise ValueError("Duplicate company IDs")
    base = companies[["id"]].rename(columns={"id": "company_id"})
    if "sector" in companies:
        base["sector"] = companies["sector"].values
    else:
        base["sector"] = np.nan
    if not sectors.empty and {"company_id", "sector"} <= set(sectors):
        sector_map = sectors.drop_duplicates("company_id").set_index("company_id")["sector"]
        base["sector"] = base["sector"].replace("", np.nan).fillna(base["company_id"].map(sector_map))
    base["sector"] = base["sector"].fillna("Unknown").replace("", "Unknown")
    if not ratios.empty:
        r = _latest(ratios)
        available = [f for f in FEATURES if f in r and f != "fcf_cagr_5yr"]
        if available:
            base = base.merge(r[["company_id", *available]], on="company_id", how="left", validate="one_to_one")
        if "fcf_cagr_5yr" in r:
            base = base.merge(r[["company_id", "fcf_cagr_5yr"]], on="company_id", how="left", validate="one_to_one")
    if not pnl.empty and "opm_percentage" in pnl:
        p = _latest(pnl)[["company_id", "opm_percentage"]].rename(columns={"opm_percentage": "source_opm"})
        base = base.merge(p, on="company_id", how="left", validate="one_to_one")
        if "operating_profit_margin_pct" not in base:
            base["operating_profit_margin_pct"] = base["source_opm"]
        else:
            base["operating_profit_margin_pct"] = base["operating_profit_margin_pct"].fillna(base["source_opm"])
        base = base.drop(columns="source_opm")
    calculated = _fcf_cagr(cf)
    if not calculated.empty:
        base = base.merge(calculated.rename(columns={"fcf_cagr_5yr": "derived_fcf_cagr"}), on="company_id", how="left", validate="one_to_one")
        if "fcf_cagr_5yr" not in base:
            base["fcf_cagr_5yr"] = base["derived_fcf_cagr"]
        else:
            base["fcf_cagr_5yr"] = base["fcf_cagr_5yr"].fillna(base["derived_fcf_cagr"])
        base = base.drop(columns="derived_fcf_cagr")
    revenue_cagr = _revenue_cagr(pnl)
    if not revenue_cagr.empty:
        base = base.merge(
            revenue_cagr.rename(columns={"revenue_cagr_5yr": "derived_revenue_cagr"}),
            on="company_id", how="left", validate="one_to_one",
        )
        if "revenue_cagr_5yr" not in base:
            base["revenue_cagr_5yr"] = base["derived_revenue_cagr"]
        else:
            base["revenue_cagr_5yr"] = base["revenue_cagr_5yr"].fillna(base["derived_revenue_cagr"])
        base = base.drop(columns="derived_revenue_cagr")
    for feature in FEATURES:
        if feature not in base:
            base[feature] = np.nan
        base[feature] = pd.to_numeric(base[feature], errors="coerce").replace([np.inf, -np.inf], np.nan)
    return base.sort_values("company_id").reset_index(drop=True)


def _revenue_cagr(pnl, years=5):
    if pnl.empty or "sales" not in pnl:
        return pd.DataFrame(columns=["company_id", "revenue_cagr_5yr"])
    pnl = pnl.copy()
    pnl["year"] = pd.to_numeric(pnl["year"], errors="coerce")
    pnl["sales"] = pd.to_numeric(pnl["sales"], errors="coerce")
    result = []
    for company, group in pnl.dropna(subset=["year", "sales"]).groupby("company_id"):
        group = group.sort_values("year").drop_duplicates("year", keep="last")
        if group.empty:
            continue
        end = group.iloc[-1]
        earlier = group[(group["year"] <= end["year"] - years) & (group["sales"] > 0)]
        growth = np.nan
        if not earlier.empty and end["sales"] > 0:
            start = earlier.iloc[-1]
            elapsed = end["year"] - start["year"]
            if elapsed > 0:
                growth = ((end["sales"] / start["sales"]) ** (1 / elapsed) - 1) * 100
        result.append({"company_id": company, "revenue_cagr_5yr": growth})
    return pd.DataFrame(result, columns=["company_id", "revenue_cagr_5yr"])


def impute_features(frame):
    """Sector median first; global median only if a whole sector lacks the metric.

    Entirely absent features are an error rather than silently fabricated zeroes.
    """
    result = frame.copy()
    for feature in FEATURES:
        if result[feature].notna().sum() == 0:
            raise ValueError(f"No observed values for {feature}; cannot impute a fully missing metric")
        sector_medians = result.groupby("sector")[feature].transform("median")
        result[feature] = result[feature].fillna(sector_medians).fillna(result[feature].median())
    if result[list(FEATURES)].isna().any().any():
        raise ValueError("Imputation left missing values")
    return result


def label_clusters(centroids):
    """Assign distinct descriptive names by a deterministic composite centroid rank."""
    # Higher profitability, growth and cash flow and lower leverage score positively.
    score = (centroids[:, 0] - centroids[:, 1] + centroids[:, 2] +
             centroids[:, 3] + centroids[:, 4])
    ranked = np.argsort(-score, kind="stable")
    return {int(cluster): ARCHETYPES[rank] for rank, cluster in enumerate(ranked)}


def generate(db_path="db/nifty100.db", output="output/cluster_labels.csv",
             elbow_path="reports/elbow_plot.png", expected_companies=92):
    frame = load_features(db_path)
    if len(frame) != expected_companies:
        raise ValueError(f"Expected {expected_companies} companies; found {len(frame)}")
    filled = impute_features(frame)
    scaled = StandardScaler().fit_transform(filled[list(FEATURES)])
    if len(scaled) < 11:
        raise ValueError("At least 11 companies are required for the k=2..10 elbow plot")
    ks = list(range(2, 11))
    inertia = [KMeans(n_clusters=k, random_state=42, n_init=10).fit(scaled).inertia_ for k in ks]
    model = KMeans(n_clusters=5, random_state=42, n_init=10).fit(scaled)
    labels = model.labels_
    names = label_clusters(model.cluster_centers_)
    distances = np.linalg.norm(scaled - model.cluster_centers_[labels], axis=1)
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    result = pd.DataFrame({"company_id": frame["company_id"], "cluster_id": labels.astype(int),
                           "cluster_name": [names[int(i)] for i in labels],
                           "distance_from_centroid": distances})
    if result["company_id"].nunique() != expected_companies or result["cluster_id"].nunique() != 5:
        raise ValueError("Clustering did not assign every company to five non-empty clusters")
    result.to_csv(output, index=False)
    elbow_path = Path(elbow_path); elbow_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(ks, inertia, marker="o")
    ax.axvline(5, linestyle="--", label="Selected k=5")
    ax.set(xlabel="Number of clusters (k)", ylabel="Inertia", title="N100 KMeans Elbow Plot")
    ax.set_xticks(ks); ax.legend(); fig.tight_layout()
    fig.savefig(elbow_path, dpi=160); plt.close(fig)
    print(f"Generated {output} ({len(result)} companies) and {elbow_path}")
    print("Review the elbow plot manually: k=5 is a specification choice, not an automatically verified elbow.")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default="db/nifty100.db")
    p.add_argument("--output", default="output/cluster_labels.csv")
    p.add_argument("--elbow", default="reports/elbow_plot.png")
    args = p.parse_args()
    generate(args.db, args.output, args.elbow)


if __name__ == "__main__":
    main()
