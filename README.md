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

The schema contains explicit targets for all 12 source datasets, including `market_cap`. The original specification says “10 tables” while listing 11 table names plus 12 source files; the implementation keeps every supplied dataset rather than silently dropping one.

### Day 05 — Full Data Load — All 12 Files

Implemented and corrected the full SQLite loading pipeline in `src/etl/database_loader.py`.

**Completed:**
- Loads all 12 Excel source files from `data/raw/`.
- Uses the Day 02 Excel loader and handles financial-year formats such as `Dec 2012` and `Mar-13`.
- Preserves the 92-company master universe from `companies.xlsx`.
- Normalizes company identifiers and resolves dependent source IDs against canonical company aliases.
- Filters dependent source rows whose company IDs are not present in the 92-company master so foreign-key integrity is maintained.
- Deduplicates annual records before inserting into tables with `UNIQUE(company_id, year)`.
- Maps source-specific columns to the normalized SQLite schema.
- Reshapes wide supplementary datasets such as analysis, pros/cons, and financial ratios into the target tables.
- Loads parent data before dependent data.
- Recreates `nifty100.db` from `db/schema.sql` on each load.
- Enables `PRAGMA foreign_keys = ON`.
- Generates `output/load_audit.csv`, including source rows, loaded rows, database rows, unmapped source rows, and status.
- Performs `PRAGMA foreign_key_check` after loading.

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

> **Execution note:** the generated audit is the source of truth for actual loaded counts, unmapped rows, and the FK-check result. Day 05/06 should only be signed off after the corrected loader has been executed and the resulting audit/manual-review results confirm the acceptance criteria.

### Day 06 — Data Quality Manual Review

Added `notebooks/day06_manual_review.sql` for the required manual review.

**Day 06 checks:**
- Select five reproducible companies for manual inspection.
- Review P&L, Balance Sheet, and Cash Flow year coverage.
- Identify companies with fewer than five P&L years.
- Compare financial-statement coverage across the 92-company universe.
- Detect orphan company IDs across dependent tables.
- Produce a compact year-coverage summary.
- Use findings to identify loader/source-mapping bugs before rerunning Day 05.

### Day 07 — Sprint Wrap-Up & Review

Added `notebooks/exploratory_queries.sql` with 10 read-only exploratory queries covering:

1. Company universe count.
2. Row counts for all populated tables.
3. Latest-year companies ranked by net profit.
4. Latest-year companies ranked by sales.
5. Latest-year average operating margin by sector.
6. Latest market-cap ranking.
7. Financial-statement year coverage by company.
8. Companies with fewer than five P&L years.
9. Latest stock-price snapshot.
10. SQLite foreign-key integrity check.

The Day 07 SQL is aligned with the current schema names (`profitandloss`, `balancesheet`, `cashflow`, `prosandcons`, etc.) and is intended for execution against the freshly generated `nifty100.db`.

**Sprint 1 review checklist:**
- `SELECT COUNT(*) FROM companies` = 92.
- `PRAGMA foreign_key_check` returns 0 rows.
- `output/load_audit.csv` contains zero CRITICAL rejections.
- 35+ ETL unit tests pass.
- Five-company manual review is correct.
- Final sprint review is signed off.

> **Verification note:** these are acceptance criteria, not claimed execution results. Run `make load`, the Day 06 review SQL, `pytest -q`, and `notebooks/exploratory_queries.sql` against the current source data before recording final sign-off.

## Data Quality Rules

The validator covers DQ-01 through DQ-16, including:
- DQ-01 primary-key uniqueness/missing IDs
- DQ-02 `(company_id, year)` uniqueness
- DQ-03 foreign-key integrity
- DQ-04 balance-sheet reconciliation
- DQ-05 operating-margin cross-check
- DQ-06 positive sales
- DQ-07 tax-rate sanity
- DQ-08 EPS sanity
- DQ-09/DQ-10 dividend checks
- DQ-11 company website validation
- DQ-12 missing EPS
- DQ-13 total assets positive
- DQ-14 PAT missing
- DQ-15 close price positive
- DQ-16 stock-date validity

## Important source-data note

The uploaded Excel files are source inputs for this project. Place the required workbooks in `data/raw/` before running the pipeline.

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

## Sprint 1 Status

**Day 07 implementation is prepared.** Final sprint sign-off remains dependent on executing the current loader, manual review, unit tests, exploratory SQL, and confirming the generated audit meets the acceptance criteria.
