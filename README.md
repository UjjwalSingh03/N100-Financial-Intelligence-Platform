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

## Sprint 2 — Financial Ratio Engine

Sprint 2 extends the platform with a reusable Financial Ratio Engine covering profitability, leverage, efficiency, growth, cash-flow quality, and capital-allocation analytics.

### Day 08 — Profitability Ratios

Implemented `src/analytics/ratios.py` for core profitability KPIs:
- Net Profit Margin (NPM) = Net Profit / Sales × 100.
- Operating Profit Margin (OPM) calculation with a cross-check against the source `opm_percentage`; differences above 1% are logged.
- Return on Equity (ROE) = Net Profit / (Equity Capital + Reserves) × 100, returning `None` for non-positive equity.
- Return on Capital Employed (ROCE) using EBIT / (Equity + Reserves + Borrowings) × 100.
- Financials-sector ROCE classification uses a sector-relative benchmark rather than a generic absolute threshold.
- Return on Assets (ROA) = Net Profit / Total Assets × 100, returning `None` when assets are zero.

Added `profitability_ratios()` and 8 unit tests covering normal calculations and denominator/edge cases.

### Day 09 — Leverage & Efficiency Ratios

Extended `src/analytics/ratios.py` with leverage and operating-efficiency KPIs:
- Debt-to-Equity (D/E) = Borrowings / (Equity Capital + Reserves).
- Debt-free companies return D/E = 0 when borrowings are zero.
- `high_leverage_flag` is raised when D/E > 5 for non-Financials companies.
- Interest Coverage Ratio (ICR) = (Operating Profit + Other Income) / Interest.
- Zero interest is handled as `None` with a `Debt Free` display label.
- ICR below 1.5 receives a warning flag.
- Net Debt = Borrowings − Investments.
- Asset Turnover = Sales / Total Assets, returning `None` when assets are zero.

Added 8 unit tests covering leverage, debt-free handling, ICR warnings, net debt, and asset turnover.

### Day 10 — CAGR Engine

Implemented `src/analytics/cagr.py` for historical growth analysis using:

```
CAGR = ((End / Start)^(1/n) - 1) × 100
```

Added Revenue, PAT, and EPS CAGR for 3-year, 5-year, and 10-year windows. The engine explicitly handles:
- Positive → Positive: normal CAGR.
- Positive → Negative: `DECLINE_TO_LOSS`.
- Negative → Positive: `TURNAROUND`.
- Negative → Negative: `BOTH_NEGATIVE`.
- Zero starting value: `ZERO_BASE`.
- Insufficient historical observations: `INSUFFICIENT`.

Separate flag fields are generated so sign changes and invalid CAGR scenarios are not represented as misleading percentages. Added 10 unit tests covering normal CAGR calculations, edge cases, insufficient data, and database-ready output columns.

### Day 12 — Populate financial_ratios Table

Implemented the full ratio-table population workflow for all available company/year records.

**Day 12 KPI columns:**
- `net_profit_margin_pct`
- `operating_profit_margin_pct`
- `return_on_equity_pct`
- `debt_to_equity`
- `interest_coverage`
- `asset_turnover`
- `free_cash_flow_cr`
- `capex_cr`
- `earnings_per_share`
- `book_value_per_share`
- `dividend_payout_ratio_pct`
- `total_debt_cr`
- `cash_from_operations_cr`
- `revenue_cagr_5yr`
- `pat_cagr_5yr`
- `eps_cagr_5yr`
- `composite_quality_score`

Run:

```bash
python scripts/populate_financial_ratios.py --db db/nifty100.db
```

The script rebuilds the wide `financial_ratios` table, populates one row per company/year, verifies that the row count is at least 1,100, and runs `PRAGMA foreign_key_check`.

**Data-source note:** the current normalized schema does not contain a dedicated dividend-payout or share-count field. The population script therefore leaves `dividend_payout_ratio_pct` and `book_value_per_share` NULL until those source fields are normalized, rather than fabricating values. EPS is taken directly from the P&L source. The 5-year CAGR values use the Day 10 CAGR engine and its sign/zero-base handling.


### Day 13 — Bank ROCE Carve-Out & Edge Case Log

Implemented the Day 13 ratio edge-case audit in `scripts/ratio_edge_case_audit.py`.

**Day 13 checks:**
- Preserves the Financials carve-out: `high_leverage_flag` remains suppressed for companies whose `broad_sector` is Financials, covering banks, NBFCs, and insurance.
- Recomputes ROCE from EBIT/operating profit divided by equity + reserves + borrowings.
- Cross-checks engine ROCE against the source `roce_percentage` field when available and logs anomalies above 5 percentage points to `output/ratio_edge_cases.log`.
- Cross-checks source ROE against the ratio-engine ROE and logs material differences for review.
- Keeps the ratio-engine ROE/ROCE values authoritative for analytics; source values are reference/display values only.
- Records each anomaly with company, year, source value, engine value, difference, and a review category.
- Uses **data source issue** for missing/invalid source or engine inputs and **formula discrepancy** when both values are valid but materially differ under the engine formula.
- **Version difference** is reserved for cases where source/version metadata confirms a historical formula or methodology change; the script does not invent that classification without evidence.
- Added tests for Financials leverage suppression and anomaly logging.

Run:

```bash
python scripts/ratio_edge_case_audit.py --db db/nifty100.db
```

The generated `output/ratio_edge_cases.log` is the review artifact. The script must be executed against the current database before recording actual anomaly counts.

### Day 11 — Cash Flow KPIs & Capital Allocation

### Day 11 — Cash Flow KPIs & Capital Allocation

Implemented `src/analytics/cash_flow.py` with:
- Free Cash Flow (CFO + CFI), including negative FCF values.
- Five-year CFO/PAT quality scoring and High Quality / Moderate / Accrual Risk labels.
- CapEx intensity and Asset Light / Moderate / Capital Intensive classification.
- FCF conversion rate with zero-operating-profit handling.
- Eight-pattern capital allocation classification from CFO, CFI, and CFF signs.
- `(+,-,-)` refinement to Shareholder Returns when CFO/PAT quality is above 1.0; otherwise Reinvestor.

Added `scripts/generate_capital_allocation.py` to generate `output/capital_allocation.csv` with:
`company_id, year, cfo_sign, cfi_sign, cff_sign, pattern_label`.

Added Day 11 unit tests in `tests/analytics/test_cash_flow.py` covering FCF, five-year CFO quality, classification thresholds, zero denominators, and capital-allocation patterns.

Run the CSV generator after loading the database:

```bash
python scripts/generate_capital_allocation.py
```
