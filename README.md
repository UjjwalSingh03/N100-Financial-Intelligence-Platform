# N100 Financial Intelligence Platform

A financial intelligence platform for Nifty 100 companies, covering data ingestion, validation, SQLite analytics, financial ratios, and reporting.

## Sprint 1 — Data Foundation

### Day 01 — Environment Setup

Established the Python project structure, dependency configuration, environment template, Makefile commands, Git ignore rules, and initial ETL/test packages.

### Day 02 — Excel Loader & Normaliser

Implemented the Excel ingestion foundation against the actual Bluestock N100 workbook layout.

**Completed and corrected:**
- `src/etl/loader.py` now reads Excel workbooks with `header=None` and detects the real schema row.
- Loader removes fully blank rows and columns and trims column names.
- Loader validates source-file existence and supported Excel extensions.
- `src/etl/normaliser.py` provides `normalize_year()` for calendar years, `FY` notation, financial-year ranges, and date-like values.
- `normalize_ticker()` handles whitespace, case, NSE/BSE prefixes, and `.NS`/`.BO` suffixes.
- Added loader tests and the existing normaliser suite covers 39 year/ticker cases.

**Actual 12 logical source workbooks:**
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

See `data/raw/README.md` for source mapping and workbook-layout notes.

### Day 03 — Schema Validator & 16 DQ Rules

Implemented and corrected the validation layer so the rules use the documented source column names and relationships.

**Completed:**
- `src/etl/validator.py` implements DQ-01 through DQ-16 with structured `ValidationFailure` records.
- CRITICAL checks cover primary-key and foreign-key integrity.
- WARNING checks cover Balance Sheet reconciliation, OPM, and positive sales.
- Added financial-data checks for tax rate, EPS, dividends, company URLs, total assets, PAT, stock prices, and dates.
- Added tests using the documented workbook field names and relationships.
- `output/validation_failures.csv` is the generated validation-output location.

**Day 02 files:**
- `src/etl/loader.py`
- `src/etl/normaliser.py`
- `tests/etl/test_loader.py`
- `tests/etl/test_normaliser.py`
- `data/raw/README.md`

**Day 03 files:**
- `src/etl/validator.py`
- `tests/etl/test_validator.py`
- `output/validation_failures.csv`

### Day 04 — SQLite Database Schema

Implemented the SQLite schema foundation in `db/schema.sql`.

**Completed:**
- Added the logical tables required by the supplied data model: `companies`, `profitandloss`, `balancesheet`, `cashflow`, `analysis`, `documents`, `prosandcons`, `sectors`, `stock_prices`, `financial_ratios`, and `peer_groups`.
- Defined primary keys for all tables.
- Defined foreign keys from child tables to `companies.id`.
- Added uniqueness constraints for annual `(company_id, year)` records and daily `(company_id, price_date)` records where applicable.
- Added indexes for common company/year and company/date lookups.
- Enabled SQLite foreign-key enforcement with `PRAGMA foreign_keys = ON`.
- Kept all 11 logical entities because the supplied Sprint 1 text says “10 tables” but separately lists 11 table names; this avoids silently dropping `peer_groups` or another required domain.

> **SQLite note:** `PRAGMA foreign_keys = ON` must be enabled on each SQLite connection. The schema includes it, and the application loader should execute it immediately after opening the connection.

## Important source-data note

The uploaded Excel files are the source inputs for this project. They are not automatically committed to GitHub by the ETL code. The repository documents the required filenames in `data/raw/README.md`; place the actual workbooks in `data/raw/` locally before running the pipeline.

## Project structure

```text
data/
  raw/          # 12 source Excel inputs
  processed/    # Cleaned/intermediate data

db/             # SQLite schema and database assets
notebooks/      # Exploratory SQL/notebooks
output/         # Generated reports and validation outputs
src/etl/        # ETL pipeline
tests/etl/      # ETL tests
```

## Setup

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and adjust local settings if required.
4. Place the 12 source Excel workbooks in `data/raw/`.

## Useful commands

```bash
make test
make load
make clean
```

## Next step

**Day 05 — Full Data Load:** load all 12 source workbooks into SQLite, generate `output/load_audit.csv`, and verify row counts and foreign-key integrity.
