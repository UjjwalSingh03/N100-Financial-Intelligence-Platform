# N100 Financial Intelligence Platform

A financial intelligence platform for Nifty 100 companies, covering data ingestion, validation, SQLite analytics, financial ratios, and reporting.

## Sprint 1 — Data Foundation

### Day 01 — Environment Setup

Established the Python project structure, dependency configuration, environment template, Makefile commands, Git ignore rules, and initial ETL/test packages.

### Day 02 — Excel Loader & Normaliser

Implemented the Excel ingestion foundation against the actual Bluestock N100 workbook layout.

**Completed and corrected:**
- `src/etl/loader.py` detects the real schema row in supplied workbooks.
- Loader removes fully blank rows/columns and trims column names.
- Loader validates source-file existence and supported Excel extensions.
- `src/etl/normaliser.py` provides `normalize_year()` and `normalize_ticker()`.
- Added loader and normaliser tests.

**12 source workbooks:**
1. `companies.xlsx`
2. `profitandloss.xlsx`
3. `balancesheet.xlsx`
4. `cashflow.xlsx`
5. `analysis.xlsx`
6. `documents.xlsx`
7. `prosandcons.xlsx`
8. `sectors.xlsx`
9. `stock_prices.xlsx`
10. `financial_ratios.xlsx`
11. `market_cap.xlsx`
12. `peer_groups.xlsx`

### Day 03 — Schema Validator & 16 DQ Rules

Implemented and corrected DQ-01 through DQ-16 with structured validation failures, PK/FK checks, financial sanity checks, tests, and `output/validation_failures.csv`.

### Day 04 — SQLite Database Schema

Implemented `db/schema.sql` with primary keys, foreign keys, uniqueness constraints, indexes, and SQLite foreign-key enforcement.

The schema now contains explicit targets for all 12 source datasets, including `market_cap`. The project specification's “10 tables” wording is inconsistent with its source list, so no supplied dataset is silently dropped.

### Day 05 — Full Data Load — All 12 Files

Implemented and corrected the full SQLite loading pipeline in `src/etl/database_loader.py`.

**Completed:**
- Loads all 12 Excel source files from `data/raw/`.
- Uses the Day 02 Excel loader and handles financial-year formats such as `Dec 2012` and `Mar-13`.
- Preserves the 92-company master universe from `companies.xlsx`.
- Filters dependent source rows whose company IDs are not present in the 92-company master so foreign-key integrity is maintained.
- Deduplicates annual records before inserting into tables with `UNIQUE(company_id, year)`.
- Maps source-specific columns to the normalized SQLite schema.
- Reshapes wide supplementary datasets such as analysis, pros/cons, and financial ratios into the target tables.
- Loads parent data before dependent data.
- Recreates `nifty100.db` from `db/schema.sql` on each load, preventing stale partial-load rows.
- Enables `PRAGMA foreign_keys = ON`.
- Generates `output/load_audit.csv`, including source rows, loaded rows, database rows, unmapped source rows, and status.
- Performs `PRAGMA foreign_key_check` after loading.
- Tracks target row-count ranges for the core datasets.

**Load order:**
1. Companies
2. Sectors
3. Peer groups
4. Profit & Loss
5. Balance Sheet
6. Cash Flow
7. Analysis
8. Documents
9. Pros & Cons
10. Stock Prices
11. Financial Ratios
12. Market Cap

> **Execution note:** the actual Excel files are intentionally not committed to GitHub. Run `make load` after placing all 12 source workbooks in `data/raw/`. The generated audit is the source of truth for actual loaded counts and the FK-check result.

## Important source-data note

The uploaded Excel files are source inputs for this project. They are not automatically committed to GitHub by the ETL code. Place the required workbooks in `data/raw/` before running the pipeline.

## Project structure

```text
data/
  raw/          # 12 source Excel inputs
  processed/    # Cleaned/intermediate data

db/
  schema.sql    # SQLite schema

nifty100.db     # Generated SQLite database (local)
notebooks/      # Exploratory SQL/notebooks
output/         # Generated audit and validation outputs
src/etl/        # ETL pipeline
tests/etl/      # ETL tests
```

## Setup

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` if required.
4. Place all 12 source Excel workbooks in `data/raw/`.
5. Run:

```bash
make load
```

## Useful commands

```bash
make test
make load
make clean
```

## Next step

**Day 06 — Manual Review & Coverage:** review five random companies, verify year coverage, identify companies with fewer than five years of data, and fix loader issues found during review.
