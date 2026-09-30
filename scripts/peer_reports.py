"""Sprint 3 Day 19/20 — radar charts and peer comparison workbook."""
from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

RADAR_METRICS = [
    ("ROE", "return_on_equity_pct"),
    ("ROCE", "roce"),
    ("NPM", "net_profit_margin_pct"),
    ("D/E", "debt_to_equity"),
    ("FCF Score", "fcf_score"),
    ("PAT CAGR 5Y", "pat_cagr_5yr"),
    ("Revenue CAGR 5Y", "revenue_cagr_5yr"),
    ("Composite Score", "composite_quality_score"),
]

PEER_METRICS = [
    ("ROE", "return_on_equity_pct"),
    ("ROCE", "roce"),
    ("NPM", "net_profit_margin_pct"),
    ("D/E", "debt_to_equity"),
    ("FCF", "free_cash_flow_cr"),
    ("PAT CAGR 5Y", "pat_cagr_5yr"),
    ("Revenue CAGR 5Y", "revenue_cagr_5yr"),
    ("EPS CAGR 5Y", "eps_cagr_5yr"),
    ("Interest Coverage", "interest_coverage"),
    ("Asset Turnover", "asset_turnover"),
]

def _norm(v):
    return re.sub(r"[^0-9a-z]+", "_", str(v).strip().lower()).strip("_")

def _resolve_peer_workbook(source: str | Path) -> Path:
    p = Path(source)
    if p.is_file():
        return p
    hits = sorted(p.glob("*peer_groups*.xlsx"))
    if not hits:
        raise FileNotFoundError(f"No peer_groups workbook found in {source}")
    if len(hits) > 1:
        raise RuntimeError(f"Ambiguous peer_groups workbooks: {[x.name for x in hits]}")
    return hits[0]

def load_memberships(source: str | Path) -> pd.DataFrame:
    df = pd.read_excel(_resolve_peer_workbook(source))
    df.columns = [_norm(c) for c in df.columns]
    aliases = {
        "group_name": "peer_group_name",
        "peer_group": "peer_group_name",
        "company": "company_id",
        "peer_company": "peer_company_id",
        "peer": "peer_company_id",
    }
    df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})
    required = {"company_id", "peer_group_name"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"peer_groups workbook missing columns: {sorted(missing)}")

    rows = []
    for _, row in df.iterrows():
        group = row.get("peer_group_name")
        if pd.isna(group):
            continue
        for col in ("company_id", "peer_company_id"):
            if col in df.columns and pd.notna(row.get(col)):
                rows.append((str(row[col]).strip(), str(group).strip()))
    return pd.DataFrame(rows, columns=["company_id", "peer_group_name"]).drop_duplicates()

def load_metrics(db_path: str | Path) -> pd.DataFrame:
    sql = """
    SELECT
        fr.company_id, fr.year,
        fr.return_on_equity_pct,
        CASE WHEN (COALESCE(bs.equity_capital,0)+COALESCE(bs.reserves,0)+COALESCE(bs.borrowings,0)) > 0
             THEN pnl.operating_profit * 100.0 /
                  (COALESCE(bs.equity_capital,0)+COALESCE(bs.reserves,0)+COALESCE(bs.borrowings,0))
        END AS roce,
        fr.net_profit_margin_pct,
        fr.debt_to_equity,
        fr.free_cash_flow_cr,
        fr.pat_cagr_5yr,
        fr.revenue_cagr_5yr,
        fr.eps_cagr_5yr,
        fr.interest_coverage,
        fr.asset_turnover,
        fr.composite_quality_score,
        c.company_name
    FROM financial_ratios fr
    JOIN companies c ON c.id = fr.company_id
    LEFT JOIN profitandloss pnl ON pnl.company_id=fr.company_id AND pnl.year=fr.year
    LEFT JOIN balancesheet bs ON bs.company_id=fr.company_id AND bs.year=fr.year
    """
    with sqlite3.connect(db_path) as con:
        return pd.read_sql_query(sql, con)

def latest_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    if metrics.empty:
        return metrics.copy()
    return metrics.sort_values(["company_id", "year"]).groupby("company_id", as_index=False).tail(1).reset_index(drop=True)

def add_fcf_score(metrics: pd.DataFrame, memberships: pd.DataFrame) -> pd.DataFrame:
    out = metrics.copy()
    out["fcf_score"] = np.nan
    merged = out.merge(memberships, on="company_id", how="left")
    for group, idx in merged.groupby("peer_group_name", dropna=True).groups.items():
        vals = pd.to_numeric(merged.loc[idx, "free_cash_flow_cr"], errors="coerce")
        valid = vals.notna()
        n = int(valid.sum())
        if n == 0:
            continue
        if n == 1:
            pct = pd.Series(0.5, index=vals.index)
        else:
            pct = pd.Series(np.nan, index=vals.index)
            pct.loc[valid] = (vals.loc[valid].rank(method="min") - 1) / (n - 1)
        merged.loc[idx, "fcf_score"] = pct * 100
    out["fcf_score"] = merged["fcf_score"].to_numpy()
    # For unassigned companies use the Nifty-100 cross-sectional FCF percentile.
    vals = pd.to_numeric(out["free_cash_flow_cr"], errors="coerce")
    valid = vals.notna()
    n = int(valid.sum())
    if n:
        pct = pd.Series(np.nan, index=out.index)
        pct.loc[valid] = 50.0 if n == 1 else (vals.loc[valid].rank(method="min") - 1) / (n - 1) * 100
        out["fcf_score"] = out["fcf_score"].fillna(pct)
    return out

def _safe_values(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for col in columns:
        result[col] = pd.to_numeric(result[col], errors="coerce")
    return result

def _radar(ax, labels, company_values, reference_values, title, reference_label):
    n = len(labels)
    angles = np.linspace(0, 2*np.pi, n, endpoint=False).tolist()
    angles += angles[:1]
    company = list(company_values) + [company_values[0]]
    reference = list(reference_values) + [reference_values[0]]
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)
    ax.plot(angles, company, linewidth=2, label="Company")
    ax.fill(angles, company, alpha=0.18)
    ax.plot(angles, reference, linewidth=1.8, linestyle="--", label=reference_label)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", "100"], fontsize=7)
    ax.set_title(title, fontsize=13, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.28, 1.12), fontsize=8)

def generate_radar_charts(db_path="db/nifty100.db", peer_groups_source="data/raw",
                          output_dir="reports/radar_charts"):
    memberships = load_memberships(peer_groups_source)
    metrics = add_fcf_score(latest_metrics(load_metrics(db_path)), memberships)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # Scale every radar axis to a comparable 0–100 percentile score within the
    # peer group. D/E is inverted. Raw values remain in the Excel report.
    value_cols = [x[1] for x in RADAR_METRICS]
    for col in value_cols:
        metrics[col] = pd.to_numeric(metrics[col], errors="coerce")

    membership_map = memberships.groupby("company_id")["peer_group_name"].first().to_dict()
    generated = []
    nifty = metrics.copy()

    def score_frame(frame):
        result = frame.copy()
        for _, col in RADAR_METRICS:
            vals = pd.to_numeric(result[col], errors="coerce")
            valid = vals.notna()
            n = int(valid.sum())
            if n <= 1:
                result[col] = 50.0
            else:
                pct = pd.Series(np.nan, index=result.index)
                pct.loc[valid] = (vals.loc[valid].rank(method="min") - 1) / (n - 1) * 100
                result[col] = pct
            if col == "debt_to_equity":
                result[col] = 100 - result[col]
        return result

    for company_id, row in metrics.set_index("company_id").iterrows():
        group = membership_map.get(company_id)
        if group:
            peers = metrics[metrics.company_id.isin(memberships.loc[
                memberships.peer_group_name == group, "company_id"
            ])]
            scored = score_frame(peers)
            company_score = scored[scored.company_id == company_id]
            if company_score.empty:
                continue
            reference = scored[[c for _, c in RADAR_METRICS]].mean(skipna=True).fillna(50).tolist()
            company_values = company_score.iloc[0][[c for _, c in RADAR_METRICS]].fillna(50).tolist()
            labels = [x[0] for x in RADAR_METRICS]
            fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"polar": True})
            _radar(ax, labels, company_values, reference, f"{company_id} — {group}", "Peer average")
        else:
            # Requirement for unassigned companies: a single-metric standalone
            # polar chart using Composite Score against the Nifty 100 average.
            company_score = float(row["composite_quality_score"]) if pd.notna(row["composite_quality_score"]) else 50.0
            nifty_avg = float(pd.to_numeric(nifty["composite_quality_score"], errors="coerce").mean())
            labels = ["Composite Score"]
            fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"polar": True})
            _radar(ax, labels, [company_score], [nifty_avg], f"{company_id} — Nifty 100 reference", "Nifty 100 average")

        fig.tight_layout()
        path = output / f"{company_id}_radar.png"
        fig.savefig(path, dpi=160, bbox_inches="tight")
        plt.close(fig)
        generated.append(path)
    return generated

def _metric_percentile(values: pd.Series, higher=True) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    valid = numeric.notna()
    n = int(valid.sum())
    result = pd.Series(np.nan, index=numeric.index)
    if n == 1:
        result.loc[valid] = 0.0
    elif n > 1:
        result.loc[valid] = (numeric.loc[valid].rank(method="min") - 1) / (n - 1)
    if not higher:
        result = 1 - result
    return result

def build_peer_comparison(db_path="db/nifty100.db", peer_groups_source="data/raw",
                          output_path="output/peer_comparison.xlsx"):
    memberships = load_memberships(peer_groups_source)
    metrics = add_fcf_score(latest_metrics(load_metrics(db_path)), memberships)
    metrics = metrics.merge(memberships, on="company_id", how="inner").drop_duplicates(
        ["company_id", "peer_group_name"]
    )
    if metrics.empty:
        raise ValueError("No peer-group companies found in the current database.")

    groups = sorted(metrics.peer_group_name.dropna().unique())
    if len(groups) != 11:
        raise ValueError(f"Expected 11 peer groups, found {len(groups)}")

    # Resolve benchmark rows from explicit benchmark columns when present.
    raw = pd.read_excel(_resolve_peer_workbook(peer_groups_source))
    raw.columns = [_norm(c) for c in raw.columns]
    benchmark_ids = set()
    for col in ("benchmark_company_id", "benchmark_id", "benchmark"):
        if col in raw.columns:
            benchmark_ids.update(raw.loc[raw[col].notna(), col].astype(str).str.strip())
    benchmark_ids.discard("nan")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for group in groups:
            frame = metrics[metrics.peer_group_name == group].copy()
            # If no explicit benchmark is supplied, use the first listed company
            # in the peer group as the workbook's deterministic benchmark.
            explicit = frame.company_id.astype(str).isin(benchmark_ids)
            benchmark = set(frame.loc[explicit, "company_id"].astype(str))
            if not benchmark:
                benchmark = {str(frame.sort_values("company_id").iloc[0].company_id)}

            rows = []
            for _, r in frame.iterrows():
                row = {"company_id": r.company_id, "company_name": r.company_name}
                for label, col in PEER_METRICS:
                    row[label] = r.get(col)
                for label, col in PEER_METRICS:
                    higher = col != "debt_to_equity"
                    pct = _metric_percentile(frame[col], higher=higher)
                    row[f"{label} Percentile"] = float(pct.loc[r.name]) if pd.notna(pct.loc[r.name]) else np.nan
                rows.append(row)
            sheet_df = pd.DataFrame(rows)

            # Summary row: peer-group median for every raw metric and percentile.
            summary = {"company_id": "PEER MEDIAN", "company_name": "Peer group median"}
            for col in sheet_df.columns[2:]:
                summary[col] = pd.to_numeric(sheet_df[col], errors="coerce").median()
            sheet_df = pd.concat([sheet_df, pd.DataFrame([summary])], ignore_index=True)
            sheet_df.to_excel(writer, sheet_name=str(group)[:31], index=False)

    wb = load_workbook(output)
    green = PatternFill("solid", fgColor="C6EFCE")
    yellow = PatternFill("solid", fgColor="FFEB9C")
    red = PatternFill("solid", fgColor="FFC7CE")
    amber = PatternFill("solid", fgColor="FFD966")
    header = PatternFill("solid", fgColor="D9EAF7")

    for group in groups:
        ws = wb[str(group)[:31]]
        ws.freeze_panes = "C2"
        ws.auto_filter.ref = ws.dimensions
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = header
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        headers = [c.value for c in ws[1]]
        pct_cols = [i + 1 for i, h in enumerate(headers) if str(h).endswith(" Percentile")]
        company_col = headers.index("company_id") + 1
        for row in range(2, ws.max_row):
            if str(ws.cell(row, company_col).value) == "PEER MEDIAN":
                continue
            for col in pct_cols:
                cell = ws.cell(row, col)
                if cell.value is None:
                    continue
                pct = float(cell.value)
                if pct >= 0.75:
                    cell.fill = green
                elif pct <= 0.25:
                    cell.fill = red
                else:
                    cell.fill = yellow

        # Highlight the benchmark company row; median remains separately styled.
        benchmark_rows = []
        # Recreate benchmark logic from the sheet values.
        for row in range(2, ws.max_row):
            cid = str(ws.cell(row, company_col).value)
            if cid in benchmark_ids:
                benchmark_rows.append(row)
        if not benchmark_rows:
            ids = [str(ws.cell(r, company_col).value) for r in range(2, ws.max_row)]
            candidates = sorted(x for x in ids if x != "PEER MEDIAN")
            if candidates:
                benchmark_rows.append(ids.index(candidates[0]) + 2)
        for row in benchmark_rows:
            for col in range(1, ws.max_column + 1):
                ws.cell(row, col).fill = amber
                ws.cell(row, col).font = Font(bold=True)

        for col in range(1, ws.max_column + 1):
            values = [str(ws.cell(r, col).value or "") for r in range(1, min(ws.max_row, 20) + 1)]
            ws.column_dimensions[get_column_letter(col)].width = min(max(max(map(len, values)) + 2, 12), 24)
        for row in range(2, ws.max_row + 1):
            ws.row_dimensions[row].height = 20

        median_row = ws.max_row
        for col in range(1, ws.max_column + 1):
            ws.cell(median_row, col).font = Font(bold=True)
    wb.save(output)
    return output, groups

def main():
    parser = argparse.ArgumentParser(description="Sprint 3 Day 19/20 peer reports")
    parser.add_argument("--db", default="db/nifty100.db")
    parser.add_argument("--peer-groups", default="data/raw")
    parser.add_argument("--radar", action="store_true")
    parser.add_argument("--excel", action="store_true")
    parser.add_argument("--radar-dir", default="reports/radar_charts")
    parser.add_argument("--excel-output", default="output/peer_comparison.xlsx")
    args = parser.parse_args()
    if not args.radar and not args.excel:
        args.radar = args.excel = True
    if args.radar:
        print(f"radar charts generated: {len(generate_radar_charts(args.db, args.peer_groups, args.radar_dir))}")
    if args.excel:
        path, groups = build_peer_comparison(args.db, args.peer_groups, args.excel_output)
        print(f"peer comparison: {path}")
        print(f"peer groups: {len(groups)}")

if __name__ == "__main__":
    main()
