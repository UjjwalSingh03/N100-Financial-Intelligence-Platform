"""Sprint 3 Day 21 — automated validation and review gate."""
from __future__ import annotations
import argparse, json, sqlite3, subprocess
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import yaml
from openpyxl import load_workbook

REQUIRED_PRESETS=["quality_compounder","value_pick","growth_accelerator","dividend_champion","debt_free_blue_chip","turnaround_watch"]
REQUIRED_PEER_METRICS={"roe","roce","net_profit_margin","debt_to_equity","free_cash_flow","pat_cagr_5yr","revenue_cagr_5yr","eps_cagr_5yr","interest_coverage","asset_turnover"}
PASS="PASS"; FAIL="FAIL"; BLOCKED="BLOCKED"

@dataclass
class Check:
    name:str
    status:str
    detail:str
    @property
    def ok(self): return self.status==PASS

def _check(name, condition, detail, blocked=False):
    if blocked: return Check(name,BLOCKED,detail)
    return Check(name,PASS if condition else FAIL,detail)

def check_dq_tests(command):
    try: p=subprocess.run(command,shell=True,text=True,capture_output=True)
    except OSError as e: return Check("DQ unit tests",BLOCKED,f"Could not start test command: {e}")
    output=(p.stdout+"
"+p.stderr).strip()
    ok=p.returncode==0 and "failed" not in output.lower()
    return _check("DQ unit tests",ok,"DQ validator tests passed with zero failures." if ok else f"Test command failed (exit {p.returncode}). {output[-1500:]}")

def check_config(root):
    candidates=[root/"config"/"screener_config.yaml",root/"screener_config.yaml"]
    path=next((p for p in candidates if p.exists()),None)
    if path is None:return Check("Screener configuration",BLOCKED,"No screener_config.yaml found.")
    try:
        cfg=yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        presets=cfg.get("presets",{})
        missing=[p for p in REQUIRED_PRESETS if p not in presets]
        return _check("Screener configuration",not missing,f"Using {path}; six required presets present." if not missing else f"Missing presets: {missing}")
    except Exception as e:return Check("Screener configuration",FAIL,f"Could not parse {path}: {e}")

def check_preset_calibration(root):
    candidates=[root/"config"/"screener_config.yaml",root/"screener_config.yaml"]
    path=next((p for p in candidates if p.exists()),None)
    if path is None:return Check("Preset calibration",BLOCKED,"No screener_config.yaml found.")
    try:
        cfg=yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        p=cfg.get("presets",{})
        value=p["value_pick"]["filters"]
        debt=p["debt_free_blue_chip"]["filters"]
        expected_value={"pe_max":30,"pb_max":5,"de_max":3,"dividend_yield_min":0}
        expected_debt={"de_max":0.01,"roe_min":10,"sales_min":5000}
        ok=value==expected_value and debt==expected_debt
        detail="Day 21 calibrated thresholds match the validated dataset contract." if ok else f"Unexpected calibration: value_pick={value}; debt_free_blue_chip={debt}"
        return _check("Preset calibration",ok,detail)
    except Exception as e:return Check("Preset calibration",FAIL,f"Could not validate calibration: {e}")

def check_quality_compounder(db_path):
    if not db_path.exists():return Check("Quality Compounder top 5",BLOCKED,f"Database not found: {db_path}")
    try:
        with sqlite3.connect(db_path) as con:
            df=pd.read_sql_query("SELECT fr.*,c.company_name FROM financial_ratios fr JOIN companies c ON c.id=fr.company_id",con)
        if df.empty:return Check("Quality Compounder top 5",BLOCKED,"financial_ratios is empty.")
        latest=df.sort_values(["company_id","year"]).groupby("company_id",as_index=False).tail(1)
        result=latest[(pd.to_numeric(latest.return_on_equity_pct,errors="coerce")>15)&(pd.to_numeric(latest.debt_to_equity,errors="coerce")<1)].copy()
        if "composite_quality_score" in result:result=result.sort_values("composite_quality_score",ascending=False)
        top=result.head(5)
        valid=len(top)>0 and (top.return_on_equity_pct>15).all() and (top.debt_to_equity<1).all()
        return _check("Quality Compounder top 5",valid,f"Top-5 manual-review candidates: {top.company_id.tolist()}; {len(result)} companies satisfy ROE > 15% and D/E < 1.")
    except Exception as e:return Check("Quality Compounder top 5",FAIL,f"Validation error: {e}")

def check_peer_rank(db_path,group="IT Services"):
    if not db_path.exists():return Check(f"{group} ROE percentile spot-check",BLOCKED,f"Database not found: {db_path}")
    try:
        with sqlite3.connect(db_path) as con:
            pp=pd.read_sql_query("SELECT company_id,peer_group_name,metric,value,percentile_rank,year FROM peer_percentiles WHERE peer_group_name=? AND lower(metric)=?",con,params=[group,"roe"])
        if pp.empty:return Check(f"{group} ROE percentile spot-check",BLOCKED,f"No ROE percentile rows found for {group}.")
        current=pp[pp.year==pp.year.max()]
        winners=set(current.loc[current.value==current.value.max(),"company_id"].astype(str))
        pct_winners=set(current.loc[current.percentile_rank==current.percentile_rank.max(),"company_id"].astype(str))
        return _check(f"{group} ROE percentile spot-check",winners.issubset(pct_winners),f"Latest year {current.year.iloc[0]}: highest-ROE={sorted(winners)}, highest-percentile={sorted(pct_winners)}.")
    except Exception as e:return Check(f"{group} ROE percentile spot-check",FAIL,f"Validation error: {e}")

def check_peer_table(db_path):
    if not db_path.exists():return Check("Peer percentile table",BLOCKED,f"Database not found: {db_path}")
    try:
        with sqlite3.connect(db_path) as con:
            groups=pd.read_sql_query("SELECT DISTINCT peer_group_name FROM peer_percentiles",con).peer_group_name.dropna().tolist()
            metrics=set(pd.read_sql_query("SELECT DISTINCT metric FROM peer_percentiles",con).metric.dropna().tolist())
        missing=REQUIRED_PEER_METRICS-metrics
        return _check("Peer percentile table",len(groups)==11 and not missing,f"Found {len(groups)} groups and {len(metrics)} required metrics." if not missing else f"Missing metrics: {sorted(missing)}; groups found: {len(groups)}.")
    except Exception as e:return Check("Peer percentile table",FAIL,f"Validation error: {e}")

def check_screener_counts(path):
    if not path.exists(): return Check("Six preset result counts", BLOCKED, f"Workbook not found: {path}")
    try:
        wb=load_workbook(path, read_only=True, data_only=True)
        expected={"Quality Compounder","Value Pick","Growth Accelerator","Dividend Champion","Debt-Free Blue Chip","Turnaround Watch"}
        bad=[]; counts={}
        for sheet in wb.sheetnames:
            rows=max(wb[sheet].max_row-1,0); counts[sheet]=rows
            if not 5 <= rows <= 50: bad.append(f"{sheet}={rows}")
        names_ok=set(wb.sheetnames)==expected
        return _check("Six preset result counts", len(wb.sheetnames)==6 and names_ok and not bad,
                      f"Six preset sheets and counts: {counts}" if names_ok and not bad else f"Sheets={wb.sheetnames}; out-of-range={bad}")
    except Exception as e:return Check("Six preset result counts", FAIL, f"Could not inspect workbook: {e}")

def check_excel(path,expected,label):
    if not path.exists():return Check(label,BLOCKED,f"Workbook not found: {path}")
    try:
        wb=load_workbook(path,read_only=True)
        return _check(label,len(wb.sheetnames)==expected,f"Found {len(wb.sheetnames)} sheets: {wb.sheetnames}.")
    except Exception as e:return Check(label,FAIL,f"Could not read workbook: {e}")

def check_radar_dir(path):
    if not path.exists():return Check("Radar chart artifacts",BLOCKED,f"Directory not found: {path}")
    charts=list(path.glob("*_radar.png"))
    return _check("Radar chart artifacts",bool(charts),f"Found {len(charts)} radar PNG files.")

def run(root,db_path,report_path,dq_command):
    checks=[check_dq_tests(dq_command),check_config(root),check_preset_calibration(root),check_quality_compounder(db_path),
            check_peer_rank(db_path,"IT Services"),check_peer_rank(db_path,"FMCG"),check_peer_table(db_path),
            check_excel(root/"output"/"screener_output.xlsx",6,"Screener workbook"),
            check_screener_counts(root/"output"/"screener_output.xlsx"),
            check_excel(root/"output"/"peer_comparison.xlsx",11,"Peer comparison workbook"),
            check_radar_dir(root/"reports"/"radar_charts")]
    summary={"passed":sum(c.ok for c in checks),"blocked":sum(c.status==BLOCKED for c in checks),"failed":sum(c.status==FAIL for c in checks),"total":len(checks)}
    lines=["# Sprint 3 Day 21 — Tests & Sprint Review","","## Automated validation","","| Check | Status | Detail |","|---|---|---|"]
    for c in checks:
        detail=c.detail.replace("|","\|").replace(chr(10)," ")
        lines.append(f"| {c.name} | **{c.status}** | {detail} |")
    lines += ["","## Definition of Done","",
              "- Six preset screeners each return 5–50 companies.",
              "- screener_output.xlsx contains six preset sheets.",
              "- peer_comparison.xlsx contains exactly 11 peer-group sheets.",
              "- Peer percentile ranks are spot-checked for IT Services and FMCG.",
              "- DQ validator tests pass with zero failures.",
              "- Sprint review/demo is completed and signed off by the team lead.",
              "","**Day 21 calibration:** Value Pick uses P/E < 30, P/B < 5, D/E < 3, Dividend Yield > 0%. Debt-Free Blue Chip uses near-zero D/E <= 0.01, ROE > 10%, Revenue > 5000 Cr. These changes are explicit in screener_config.yaml and covered by the preset calibration check.","",
              f"**Automated result:** {summary['passed']}/{summary['total']} checks passed; {summary['blocked']} blocked; {summary['failed']} failed.","",
              "Team-lead sign-off is intentionally a human review action and is not inferred by this script."]
    report_path.parent.mkdir(parents=True,exist_ok=True); report_path.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return checks,summary

def main():
    p=argparse.ArgumentParser(description="Sprint 3 Day 21 automated validation")
    p.add_argument("--db",default="db/nifty100.db");p.add_argument("--report",default="output/day21_sprint_review.md")
    p.add_argument("--pytest-cmd",default="pytest -q tests/etl/test_validator.py")
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    checks,summary=run(root,Path(a.db),root/a.report,a.pytest_cmd)
    for c in checks:print(f"[{c.status}] {c.name}: {c.detail}")
    print("SUMMARY:",json.dumps(summary,sort_keys=True))
    return 0 if summary["failed"]==0 and summary["blocked"]==0 else 1
if __name__=="__main__":raise SystemExit(main())
