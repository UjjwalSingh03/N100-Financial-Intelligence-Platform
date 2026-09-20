"""
N100 Financial Intelligence Platform — Day 05 loader.

Loads the 12 source workbooks into SQLite with *enforced* foreign keys.

Day 05 contract:
  1. Load the 92-company master first.
  2. Build the canonical company-ID map from it (incl. known alias repairs).
  3. Detect child records whose company_id is not in the map.
  4. Do NOT insert orphan records into the fact/dimension tables.
  5. Report them in load_audit.csv as `unmapped_rows` (+ unmapped_company_ids).
  6. Quarantine the rejected rows in `unmapped_records` so nothing is lost.
  7. PRAGMA foreign_key_check must return 0 against a schema that actually
     declares the FKs — this loader declares them, so the check is meaningful.

Run:  python database_loader.py [--source DIR] [--out DIR]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import os
import re
import sqlite3
import sys

import pandas as pd

# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------
# header_row: the 7 "core" exports carry a banner line above the real header
# ("Bluestock Fintech — Nifty 100 | Profit & Loss | 1,276 records"), so their
# header lives on row index 1. The 5 supplementary files are clean at row 0.

SOURCES = [
    # (table,            filename_contains,   header_row, layer,           expected_source_rows)
    ("companies",        "companies",         1, "core",          92),
    ("sectors",          "sectors",           0, "supplementary", 92),
    ("peer_groups",      "peer_groups",       0, "supplementary", 56),
    ("analysis",         "analysis",          1, "core",           20),
    ("pros_and_cons",    "prosandcons",       1, "core",           16),
    ("documents",        "documents",         1, "core",          1585),
    ("profit_and_loss",  "profitandloss",     1, "core",          1276),
    ("balance_sheet",    "balancesheet",      1, "core",          1312),
    ("cash_flow",        "cashflow",          1, "core",          1187),
    ("financial_ratios", "financial_ratios",  0, "supplementary", 1184),
    ("market_cap",       "market_cap",        0, "supplementary", 552),
    ("stock_prices",     "stock_prices",      0, "supplementary", 5520),
]

MASTER = "companies"

# Known ticker aliases in the source data -> canonical companies.id.
# AGTL is a transposition of ATGL (Adani Total Gas); ATGL is in the master and
# has no cash_flow rows of its own, so the repair cannot collide.
ALIASES = {"AGTL": "ATGL"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def norm_col(c) -> str:
    c = re.sub(r"[^0-9a-z]+", "_", str(c).strip().lower())
    return c.strip("_")


def sql_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "INTEGER"
    if pd.api.types.is_integer_dtype(series):
        return "INTEGER"
    if pd.api.types.is_float_dtype(series):
        return "REAL"
    return "TEXT"


def md5_short(path: str, n: int = 12) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:n]


def resolve(source_dir: str, needle: str) -> str:
    hits = [f for f in sorted(os.listdir(source_dir)) if needle in f and f.endswith(".xlsx")]
    if not hits:
        raise FileNotFoundError(f"no source workbook matching '{needle}' in {source_dir}")
    if len(hits) > 1:
        raise RuntimeError(f"ambiguous source for '{needle}': {hits}")
    return os.path.join(source_dir, hits[0])


def read_clean(path: str, header_row: int) -> pd.DataFrame:
    df = pd.read_excel(path, header=header_row)
    df.columns = [norm_col(c) for c in df.columns]
    df = df.loc[:, [c for c in df.columns if c and not c.startswith("unnamed")]]
    df = df.dropna(how="all")
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(lambda v: v.strip() if isinstance(v, str) else v)
            df[col] = df[col].replace({"": None, "nan": None, "NaN": None})
    return df.reset_index(drop=True)


def create_table(con: sqlite3.Connection, table: str, df: pd.DataFrame) -> None:
    cols = []
    for c in df.columns:
        t = sql_type(df[c])
        if c == "id":
            cols.append(f'"id" {"INTEGER" if t == "INTEGER" else "TEXT"} PRIMARY KEY')
        elif c == "company_id":
            cols.append('"company_id" TEXT NOT NULL')
        else:
            cols.append(f'"{c}" {t}')
    if table == MASTER:
        ddl = f'CREATE TABLE "{table}" (\n  ' + ",\n  ".join(cols) + "\n)"
    else:
        cols.append(f'FOREIGN KEY ("company_id") REFERENCES "{MASTER}"("id")')
        ddl = f'CREATE TABLE "{table}" (\n  ' + ",\n  ".join(cols) + "\n)"
    con.execute(f'DROP TABLE IF EXISTS "{table}"')
    con.execute(ddl)


# ---------------------------------------------------------------------------
# Main load
# ---------------------------------------------------------------------------


def run(source_dir: str, out_dir: str, db_name: str = "nifty100.db") -> int:
    os.makedirs(out_dir, exist_ok=True)
    db_path = os.path.join(out_dir, db_name)
    if os.path.exists(db_path):
        os.remove(db_path)

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")

    run_ts = _dt.datetime.now().isoformat(timespec="seconds")
    canonical: set[str] = set()
    audit: list[dict] = []
    quarantine: list[pd.DataFrame] = []

    for order, (table, needle, hdr, layer, expected_src) in enumerate(SOURCES, start=1):
        path = resolve(source_dir, needle)
        df = read_clean(path, hdr)
        rows_in = len(df)

        aliases_applied = 0
        unmapped_rows = 0
        unmapped_ids = ""

        if table == MASTER:
            # Step 1 + 2 — master first, canonical map built from it.
            canonical = set(df["id"].astype(str))
            if len(canonical) != len(df):
                raise RuntimeError("duplicate company ids in master — cannot build canonical map")
        else:
            if not canonical:
                raise RuntimeError(f"{table} loaded before master — check SOURCES order")
            df["company_id"] = df["company_id"].astype(str)
            hit = df["company_id"].isin(ALIASES)
            aliases_applied = int(hit.sum())
            df.loc[hit, "company_id"] = df.loc[hit, "company_id"].map(ALIASES)

            # Step 3 + 4 — detect orphans, hold them back from the insert.
            orphan_mask = ~df["company_id"].isin(canonical)
            unmapped_rows = int(orphan_mask.sum())
            if unmapped_rows:
                bad = df.loc[orphan_mask].copy()
                unmapped_ids = ";".join(sorted(bad["company_id"].unique()))
                q = pd.DataFrame(
                    {
                        "target_table": table,
                        "source_file": os.path.basename(path).split("-", 2)[-1],
                        "source_row_id": bad["id"].astype(str).values,
                        "unmapped_company_id": bad["company_id"].values,
                        "reason": "company_id not present in companies master",
                        "rejected_at": run_ts,
                    }
                )
                quarantine.append(q)
                df = df.loc[~orphan_mask].reset_index(drop=True)

        create_table(con, table, df)
        df.to_sql(table, con, if_exists="append", index=False)
        con.commit()
        loaded = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]

        assert loaded == rows_in - unmapped_rows, f"{table}: insert count mismatch"

        audit.append(
            dict(
                load_order=order,
                layer=layer,
                source_file=os.path.basename(path).split("-", 2)[-1],
                source_md5=md5_short(path),
                target_table=table,
                columns=len(df.columns),
                rows_in_file=rows_in,
                expected_source_rows=expected_src,
                source_count_match="PASS" if rows_in == expected_src else "FAIL",
                aliases_applied=aliases_applied,
                unmapped_rows=unmapped_rows,
                unmapped_company_ids=unmapped_ids,
                rows_loaded=loaded,
                fk_enforced="yes" if table != MASTER else "n/a (parent)",
                loaded_at=run_ts,
            )
        )
        print(
            f"{order:>2}. {table:<17} in={rows_in:<5} unmapped={unmapped_rows:<4} loaded={loaded:<5}"
        )

    # Step 6 — quarantine table inside the DB (no FK, by design).
    con.execute("DROP TABLE IF EXISTS unmapped_records")
    con.execute(
        """CREATE TABLE unmapped_records (
             target_table TEXT, source_file TEXT, source_row_id TEXT,
             unmapped_company_id TEXT, reason TEXT, rejected_at TEXT)"""
    )
    if quarantine:
        qdf = pd.concat(quarantine, ignore_index=True)
        qdf.to_sql("unmapped_records", con, if_exists="append", index=False)
        qdf.to_csv(os.path.join(out_dir, "unmapped_records.csv"), index=False)
    else:
        qdf = pd.DataFrame()
    con.commit()

    # Step 7 — meaningful FK check, against a schema that declares the FKs.
    violations = con.execute("PRAGMA foreign_key_check").fetchall()
    fk_count = len(violations)

    aud = pd.DataFrame(audit)
    aud["fk_violations_after_load"] = fk_count
    aud["fk_status"] = "PASS" if fk_count == 0 else "FAIL"
    aud.to_csv(os.path.join(out_dir, "load_audit.csv"), index=False)

    declared = con.execute(
        "SELECT COUNT(*) FROM pragma_foreign_key_list('profit_and_loss')"
    ).fetchone()[0]

    print("\n--- Day 05 sign-off ---")
    print(f"tables loaded            : {len(SOURCES)}")
    print(f"rows loaded              : {int(aud.rows_loaded.sum())}")
    print(f"unmapped rows quarantined: {int(aud.unmapped_rows.sum())}")
    if len(qdf):
        print(f"unmapped company ids     : {sorted(qdf.unmapped_company_id.unique())}")
    print(f"FK declared on children  : {'yes' if declared else 'NO — schema wrong'}")
    print(f"PRAGMA foreign_key_check : {fk_count} violations")
    con.close()
    return 0 if fk_count == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="/mnt/user-data/uploads")
    ap.add_argument("--out", default="/mnt/user-data/outputs")
    a = ap.parse_args()
    return run(a.source, a.out)


if __name__ == "__main__":
    sys.exit(main())
