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
- Generates `output/load_audit.csv`.
- Performs `PRAGMA foreign_key_check` after loading.

### Day 06 — Data Quality Manual Review

Added `notebooks/day06_manual_review.sql` for the required manual review.

### Day 07 — Sprint Wrap-Up & Review

Added `notebooks/exploratory_queries.sql` with 10 read-only exploratory queries covering the company universe, row counts, rankings, coverage, stock prices, and FK integrity.

## Data Quality Rules

The validator covers DQ-01 through DQ-16, including primary-key uniqueness, company/year uniqueness, FK integrity, balance-sheet reconciliation, operating-margin cross-checks, sales/PAT/EPS checks, dividend checks, website validation, close-price sanity, and stock-date validity.

## Important source-data note

The uploaded Excel files are source inputs for this project. Place the required workbooks in `data/raw/` before running the pipeline.

## Project structure

```text
data/
  raw/          # 12 source Excel inputs
  processed/    # Cleaned/intermediate data

db/
  schema.sql    # SQLite schema
  nifty100.db   # Generated SQLite database

notebooks/      # Exploratory SQL/notebooks
output/         # Generated audit, validation, and analytics outputs
src/etl/        # ETL pipeline
src/analytics/  # Financial analytics
src/screener/   # Screener engine
src/dashboard/  # Streamlit dashboard
src/nlp/        # NLP parsing and generation
tests/          # Automated tests
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

## Sprint 2 — Financial Ratio Engine

Sprint 2 added profitability, leverage, efficiency, CAGR, cash-flow quality, capital-allocation, and composite-quality analytics through `src/analytics/`.

### Day 10 — CAGR Engine

Implemented `src/analytics/cagr.py` with 3-year, 5-year, and 10-year Revenue, PAT, and EPS CAGR handling, including turnaround, decline-to-loss, both-negative, zero-base, and insufficient-data cases.

### Day 11 — Cash Flow KPIs & Capital Allocation

Implemented `src/analytics/cash_flow.py` with FCF, CFO/PAT quality, CapEx intensity, FCF conversion, and eight capital-allocation patterns.

### Day 12 — Populate financial_ratios Table

Implemented the full ratio-table population workflow for all available company/year records, including `revenue_cagr_5yr`, `pat_cagr_5yr`, and `eps_cagr_5yr`.

## Sprint 3 — Screener & Peer Comparison Engine

Sprint 3 implemented the configurable screener, six presets, composite quality scoring, peer percentiles, radar charts, and peer-comparison workbook.

### Day 15 — Filter Engine Core

Implemented `src/screener/engine.py` with 15 configurable financial filters and Financials D/E handling.

### Day 16 — Six Preset Screeners

Added Quality Compounder, Value Pick, Growth Accelerator, Dividend Champion, Debt-Free Blue Chip, and Turnaround Watch presets.

### Day 17 — Composite Score & Export

Implemented sector-relative composite scoring and screener workbook export.

### Day 18 — Peer Percentile Rankings

Implemented `src/analytics/peer.py` for 11 peer groups and 10 required peer metrics.

### Day 19 — Radar Charts

Implemented `scripts/peer_reports.py` radar-chart generation.

### Day 20 — Peer Comparison Excel Report

Implemented the 11-sheet peer-comparison workbook.

### Day 21 — Automated Validation & Sprint 3 Review

Implemented `scripts/day21_sprint_review.py`, contract tests, review documentation, and GitHub Actions validation.

## Sprint 4 — Dashboard & Valuation Module

Sprint 4 implemented the eight-screen Streamlit dashboard, valuation analytics, integration QA, and documentation.

### Day 22 — Streamlit App Scaffold

Implemented `src/dashboard/app.py`, shared cached database helpers, and all eight dashboard screens.

### Day 23 — Home & Company Profile

Implemented six KPI tiles, sector distribution, top-quality companies, company search, historical charts, and pros/cons.

### Day 24 — Screener & Peer Comparison

Implemented ten live screener sliders, six presets, CSV export, peer-group selection, and eight-metric radar comparison.

### Day 25 — Remaining Dashboard Screens

Implemented Trends, Sectors, Capital Allocation, and Annual Reports screens with schema-safe cached database helpers.

### Day 26 — Valuation Module

Implemented `src/analytics/valuation.py` with FCF yield, P/E vs sector median, 5-year median P/E, P/B, EV/EBITDA, and valuation flags. Generates `output/valuation_summary.xlsx` and `output/valuation_flags.csv`.

### Day 27 — Integration QA & Bug Fixes

Added `scripts/day27_qa.py`, representative ticker checks, partial-history handling, N/A display handling, schema/alias fixes, and performance checks.

### Day 28 — Retro & Documentation

Added Sprint 4 retrospective and task-board documentation, complete dashboard screen descriptions, and final acceptance preparation.

## Sprint 5 — Cash Flow Intelligence + Reports + NLP

Sprint 5 covers Cash Flow Intelligence, company/sector reports, and NLP-generated financial insights.

### Day 29 — NLP Analysis Text Parser

Implemented the Day 29 NLP analysis-text parsing foundation.

**Deliverables:**
- `src/nlp/parser.py` parses these `analysis.xlsx` fields:
  - `compounded_sales_growth`
  - `compounded_profit_growth`
  - `stock_price_cagr`
  - `roe`
- Uses the required regex:
  `(\\d+)\\s*Years?:?\\s*([\\d.]+)%`
- Generates `output/analysis_parsed.csv` with exactly:
  `company_id, metric_type, period_years, value_pct`.
- Logs unmatched target text or missing target fields to `output/parse_failures.csv`.
- Cross-validates 5-year sales/profit CAGR values against the Ratio Engine's `revenue_cagr_5yr` and `pat_cagr_5yr`.
- Flags divergences greater than 5 percentage points as `MANUAL_REVIEW` in `output/cagr_divergences.csv`.
- Added automated contract tests in `tests/nlp/test_parser.py`.
- Added `src/nlp/__init__.py`.

**Run:**

```bash
python -m src.nlp.parser --analysis data/raw/analysis.xlsx --db db/nifty100.db --output-dir output
```

The parser does not fabricate missing source data. The source `analysis.xlsx` must be available in `data/raw/` before generating production CSV outputs.

## Sprint Status

**Sprint 5 Day 29 implementation is committed.** The production parse outputs should be generated only after the actual `analysis.xlsx` source workbook is available in `data/raw/`.

## Validation principle

Implementation commits and contract tests do not by themselves constitute production-data sign-off. Record actual row counts, parse-failure counts, divergence counts, report counts, and human review status only after executing the corresponding commands against the current project inputs.
