# N100 Financial Intelligence Platform

A financial intelligence platform for Nifty 100 companies, covering data ingestion, validation, SQLite analytics, financial ratios, and reporting.

## Sprint 1 — Data Foundation

### Day 01 — Environment Setup

Established the Python project structure, dependency configuration, environment template, Makefile commands, Git ignore rules, and initial ETL/test packages.

### Day 02 — Excel Loader & Normaliser

Implemented the Excel ingestion foundation against the actual Bluestock N100 workbook layout.

**Completed and corrected:**
- `src/etl/loader.py` now reads Excel workbooks with `header=None` and detects the real schema row. This fixes the supplied workbooks where a descriptive title row appears before the headers.
- Loader removes fully blank rows and columns and trims column names.
- Loader validates source-file existence and supported Excel extensions.
- `src/etl/normaliser.py` provides `normalize_year()` for calendar years, `FY` notation, financial-year ranges, and date-like values such as `Mar 2024`.
- `normalize_ticker()` handles whitespace, case, NSE/BSE prefixes, and `.NS`/`.BO` suffixes without altering the identifier itself.
- Added loader tests for title-row detection, blank-row/column cleanup, missing files, unsupported extensions, and deterministic discovery.
- Existing normaliser tests cover **39 year/ticker cases**.

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

See `data/raw/README.md` for the source mapping and the important workbook-layout notes.

### Day 03 — Schema Validator & 16 DQ Rules

Implemented and corrected the validation layer so the rules use the **actual column names and relationships in the supplied Excel files**.

**Completed and corrected:**
- `src/etl/validator.py` implements DQ-01 through DQ-16 with structured `ValidationFailure` records.
- **DQ-01:** physical `id` primary-key uniqueness/missing-value check.
- **DQ-02:** `(company_id, year)` uniqueness/missing-value check for annual datasets.
- **DQ-03:** foreign keys correctly reference `companies.id`; the supplied data uses ticker symbols such as `ABB` as company IDs.
- **DQ-04:** balance-sheet reconciliation correctly calculates equity as `equity_capital + reserves` when using the supplied schema, with a 1% tolerance.
- **DQ-05:** OPM validation correctly uses the supplied `opm_percentage` column.
- **DQ-06:** sales must be positive.
- **DQ-07:** tax percentage range validation.
- **DQ-08:** EPS sanity validation.
- **DQ-09/DQ-10:** dividend-payout validation for negative and out-of-range values.
- **DQ-11:** company website validation.
- **DQ-12:** missing EPS detection.
- **DQ-13:** non-positive total-assets detection.
- **DQ-14:** missing net-profit/PAT detection.
- **DQ-15:** non-positive stock close-price detection.
- **DQ-16:** invalid/missing stock-price date detection.
- Fixed a validator bug where generic numeric coercion prevented URL/date checks and missing EPS/PAT checks from working correctly.
- Added tests using the real workbook field names and relationships.
- `output/validation_failures.csv` remains the generated validation-output location; actual findings should be produced only after running the validator against the uploaded source data.

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

## Important source-data note

The uploaded Excel files are the **source inputs** for this project. They are not automatically committed to GitHub by the ETL code. The repository documents the required filenames in `data/raw/README.md`; place the actual workbooks in `data/raw/` locally before running the pipeline.

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

**Day 04 — SQLite Schema:** implement `db/schema.sql`, create the SQLite database structure, define PK/FK relationships, and enable foreign-key enforcement.
