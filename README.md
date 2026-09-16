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

**Day 03 — Schema Validator:** implement DQ-01 through DQ-16 validation rules, generate `validation_failures.csv`, and resolve CRITICAL data-quality failures.
