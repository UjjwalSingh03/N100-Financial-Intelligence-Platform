# N100 Financial Intelligence Platform

A financial intelligence platform for Nifty 100 companies, covering data ingestion, validation, SQLite analytics, financial ratios, and reporting.

## Sprint 1 — Data Foundation

### Day 01 — Environment Setup

Established the Python project structure, dependency configuration, environment template, Makefile commands, Git ignore rules, and initial ETL/test packages.

### Day 02 — Excel Loader & Normaliser

Implemented the Excel ingestion foundation and normalization utilities required for the N100 financial-data pipeline.

**Completed:**
- Implemented `src/etl/loader.py` to discover and load Excel workbooks from `data/raw/`.
- Added validation for supported Excel file extensions and missing source files.
- Removed fully blank rows and columns during ingestion.
- Standardized column names by trimming whitespace.
- Added `normalize_year()` for calendar years, FY notation, financial-year ranges, and date-like values.
- Added `normalize_ticker()` for trimming, uppercase conversion, exchange-prefix removal, suffix cleanup, and whitespace normalization.
- Added **39 parameterized/unit test cases** covering valid, invalid, missing, and edge-case year/ticker values.

**Day 02 files:**
- `src/etl/loader.py`
- `src/etl/normaliser.py`
- `tests/etl/test_normaliser.py`

### Day 03 — Schema Validator & 16 DQ Rules

Implemented the Sprint 1 data-quality validation foundation covering DQ-01 through DQ-16.

**Completed:**
- Added `src/etl/validator.py` with deterministic DQ-01–DQ-16 validation rules.
- Classified primary-key and foreign-key integrity failures as **CRITICAL**.
- Added **WARNING** checks for OPM consistency, balance-sheet reconciliation, and positive sales.
- Added additional financial-domain sanity checks for tax rate, EPS, dividends, URL format, assets, PAT, stock prices, and dates.
- Added `tests/etl/test_validator.py` covering PK, composite-key, FK, balance, OPM, sales, optional rules, and CSV output behavior.
- Added `output/validation_failures.csv` as the validation-report output template.

**Day 03 files:**
- `src/etl/validator.py`
- `tests/etl/test_validator.py`
- `output/validation_failures.csv`

## Project structure

```text
data/
  raw/          # Source Excel files
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
4. Put source Excel files in `data/raw/`.

## Useful commands

```bash
make test
make load
make clean
```

## Next step

**Day 04 — SQLite Schema:** implement `db/schema.sql`, create the SQLite database structure, define PK/FK relationships, and enable foreign-key enforcement.
