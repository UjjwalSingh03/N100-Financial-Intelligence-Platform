"""Day 32: audit Sprint 2 capital allocation and generate annual pattern reports."""
from __future__ import annotations
import argparse
import sqlite3
from pathlib import Path
import pandas as pd

PATTERNS = ("Reinvestor", "Shareholder Returns", "Liquidating Assets",
            "Distress Signal", "Growth Funded by Debt", "Cash Accumulator",
            "Pre-Revenue", "Mixed")
REQUIRED = ("company_id", "year", "cfo_sign", "cfi_sign", "cff_sign", "pattern_label")


def run(db_path="db/nifty100.db", csv_path="output/capital_allocation.csv",
        output_dir="output", repair=False):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    missing_cols = set(REQUIRED) - set(data.columns)
    if missing_cols:
        raise ValueError(f"Missing columns: {sorted(missing_cols)}")
    data = data.loc[:, list(REQUIRED)].copy()
    data["company_id"] = data.company_id.str.strip()
    data["year"] = data.year.str.strip()
    data["pattern_label"] = data.pattern_label.str.strip()
    with sqlite3.connect(db_path) as con:
        universe = set(pd.read_sql_query("SELECT id FROM companies", con).iloc[:, 0].astype(str))
        expected = pd.read_sql_query("SELECT company_id, year FROM cashflow", con)
    expected["company_id"] = expected.company_id.astype(str)
    expected["year"] = expected.year.astype(str)
    expected_keys = set(map(tuple, expected[["company_id", "year"]].to_numpy()))
    blank = data[(data.company_id == "") | (data.year == "")]
    duplicates = data[data.duplicated(["company_id", "year"], keep=False)]
    invalid = data[~data.pattern_label.isin(PATTERNS)]
    if repair:
        # Only drop incomplete rows and byte-identical duplicate records; never guess conflicts.
        data = data[(data.company_id != "") & (data.year != "")].drop_duplicates()
        duplicates = data[data.duplicated(["company_id", "year"], keep=False)]
    actual_keys = set(map(tuple, data[["company_id", "year"]].to_numpy()))
    missing = sorted(expected_keys - actual_keys)
    extra = sorted(actual_keys - expected_keys)
    issues = []
    for name, n in (("blank_company_or_year", len(blank)), ("duplicate_company_year", len(duplicates)),
                    ("invalid_pattern", len(invalid)), ("missing_cashflow_keys", len(missing)),
                    ("unexpected_keys", len(extra)), ("missing_companies", len(universe - set(data.company_id))),
                    ("universe_not_92", int(len(universe) != 92))):
        issues.append({"check": name, "count": n})
    pd.DataFrame(issues).to_csv(out / "capital_allocation_audit.csv", index=False)
    if duplicates.empty is False or len(invalid) or missing or extra or len(universe) != 92 or set(data.company_id) != universe or (len(blank) and not repair):
        raise ValueError("Capital allocation audit failed; see output/capital_allocation_audit.csv. "
                         "Use --repair only for blank rows and identical duplicates; resolve all other issues at source.")
    data["year"] = data.year.astype(int)
    latest = int(data.year.max())
    latest_rows = data[data.year == latest]
    if len(latest_rows) != 92 or set(latest_rows.company_id) != universe:
        raise ValueError(f"Latest year {latest} covers {len(latest_rows)} rows, not all 92 companies.")
    distribution = latest_rows.pattern_label.value_counts().reindex(PATTERNS, fill_value=0)
    pd.DataFrame({"year": latest, "pattern_label": PATTERNS,
                  "company_count": distribution.to_numpy()}).to_csv(out / "pattern_distribution.csv", index=False)
    ordered = data.sort_values(["company_id", "year"]).copy()
    ordered["previous_year"] = ordered.groupby("company_id").year.shift()
    ordered["previous_pattern"] = ordered.groupby("company_id").pattern_label.shift()
    changes = ordered[(ordered.previous_year == ordered.year - 1) &
                      (ordered.previous_pattern != ordered.pattern_label)].copy()
    changes["change_description"] = changes.previous_pattern + " -> " + changes.pattern_label
    changes = changes.rename(columns={"pattern_label": "current_pattern"})
    changes[["company_id", "previous_year", "year", "previous_pattern",
             "current_pattern", "change_description"]].to_csv(out / "pattern_changes.csv", index=False)
    workbook = out / "cashflow_intelligence.xlsx"
    if not workbook.exists():
        raise FileNotFoundError(f"{workbook} missing; run Day 31 cashflow_kpis first.")
    intelligence = pd.read_excel(workbook, sheet_name="Cash Flow Intelligence")
    if "company_id" not in intelligence:
        raise ValueError("Day 31 workbook has no company_id column.")
    lookup = latest_rows.set_index("company_id").pattern_label
    intelligence["capital_allocation_label"] = intelligence.company_id.map(lookup)
    if intelligence.capital_allocation_label.isna().any():
        raise ValueError("Workbook contains company IDs absent from latest allocation.")
    with pd.ExcelWriter(workbook, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        intelligence.to_excel(writer, sheet_name="Cash Flow Intelligence", index=False)
    if repair:
        data.loc[:, list(REQUIRED)].to_csv(csv_path, index=False)
    print(f"Day 32 complete: {latest}; {len(latest_rows)} companies; {len(changes)} year-over-year changes.")
    return latest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="db/nifty100.db")
    parser.add_argument("--capital-allocation", default="output/capital_allocation.csv")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--repair", action="store_true", help="Remove blank-key rows and identical duplicates only")
    args = parser.parse_args()
    run(args.db, args.capital_allocation, args.output_dir, args.repair)
