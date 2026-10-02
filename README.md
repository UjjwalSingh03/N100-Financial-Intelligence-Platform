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

### Day 14 — Tests & Sprint Review

Implemented the Sprint 2 validation and review gate in `scripts/day14_sprint_review.py`.

**Day 14 validation checks:**
- Runs the existing ratio, CAGR, and cash-flow formula test suites and requires at least 20 passing formula tests with zero pytest failures.
- Checks `financial_ratios` row count (>= 1,100), required KPI columns, null-only KPI columns, and SQLite foreign-key integrity.
- Runs the latest-year screener preview: ROE > 15% and D/E < 1, reporting the result count and first five rows for business review.
- Validates `output/ratio_edge_cases.log` so every anomaly entry has a supported category and explanation.
- Confirms `output/capital_allocation.csv` exists.
- Returns a non-zero exit code when any Definition-of-Done gate is blocked; it does not fabricate sprint sign-off.

Run:

```bash
python scripts/day14_sprint_review.py --db db/nifty100.db
```

Added `notebooks/day14_demo.sql` to display five latest-year companies with the computed KPI columns and `docs/sprint2_retrospective.md` for formula decisions and edge-case resolutions.

Added `src/analytics/cashflow_kpis.py` as a compatibility module that exposes the Day 11 cash-flow KPI implementation under the deliverable filename requested by the sprint specification.

> **Execution note:** the Day 14 runner is committed, but final status, screener count, row count, null-only columns, anomaly review, and team-lead sign-off must be based on executing it against the current `db/nifty100.db`. The repository does not claim those results until the command is actually run.


## Sprint 3 — Screener & Peer Comparison Engine

Sprint 3 builds the configurable financial screener and peer-comparison workflow for Nifty 100 companies.

### Day 15 — Filter Engine Core

Implemented the config-driven screener in src/screener/engine.py.

**Day 15 capabilities:**
- Loads thresholds and six preset definitions from screener_config.yaml.
- Supports all 15 required filter metrics: ROE minimum, D/E maximum, FCF minimum, Revenue CAGR 5-year minimum, PAT CAGR 5-year minimum, OPM minimum, P/E maximum, P/B maximum, Dividend Yield minimum, ICR minimum, Market Cap minimum, Net Profit minimum, EPS CAGR minimum, Asset Turnover minimum, and Sales minimum.
- Automatically skips the D/E threshold for companies in the Financials sector.
- Treats missing/Debt Free ICR values as infinity so they pass any ICR minimum.
- Supports named presets plus custom threshold overrides.
- Returns a deterministic DataFrame sorted by composite_quality_score descending.
- Added Day 15 unit tests covering Financials D/E handling, Debt Free ICR, combined filters, sorting, invalid filters, missing metrics, YAML presets, and overrides.

**Files added:**
- src/screener/engine.py
- src/screener/__init__.py
- screener_config.yaml
- tests/screener/test_engine.py

**Usage:**

    from src.screener.engine import screen

    result = screen(
        financial_ratios_df,
        preset="quality",
        thresholds={"roe_min": 20},
    )

> **Execution note:** Day 15 implementation and unit-test coverage are committed. The engine expects valuation/market metrics such as P/E, P/B, Dividend Yield, Market Cap, Net Profit, and Sales to be present in the input DataFrame when those filters are selected; it does not fabricate missing source metrics.

### Day 16 — Six Preset Screeners

Added six Sprint 3 preset screeners to `screener_config.yaml`:

1. **Quality Compounder** — ROE > 15%, D/E < 1.0, FCF > 0, Revenue CAGR 5Y > 10%.
2. **Value Pick** — P/E < 20, P/B < 3.0, D/E < 2.0, Dividend Yield > 1%.
3. **Growth Accelerator** — PAT CAGR 5Y > 20%, Revenue CAGR 5Y > 15%, D/E < 2.0.
4. **Dividend Champion** — Dividend Yield > 2%, Dividend Payout < 80%, FCF > 0.
5. **Debt-Free Blue Chip** — D/E = 0, ROE > 12%, Sales/Revenue > ₹5,000 crore.
6. **Turnaround Watch** — Revenue CAGR 3Y > 10%, positive latest-year FCF, and declining D/E year-over-year.

The Day 15 engine was extended with exact-value, dividend-payout, 3-year CAGR, and D/E trend filters. The D/E trend rule compares each company's chronologically ordered observations and keeps periods where D/E is lower than the preceding observation.

**Review requirement:** each preset must be executed against the full 92-company universe. The required 5–50 result-count range and business-sense review are acceptance criteria and are not claimed as executed until the current production dataset is screened.

### Day 17 — Composite Score & Export

Implemented the Sprint 3 composite quality scoring and Excel export foundation.

**Composite score weights**
- Profitability: 35% — ROE 15%, ROCE 10%, NPM 10%
- Cash Quality: 30% — FCF CAGR 15%, CFO/PAT 10%, FCF-positive flag 5%
- Growth: 20% — Revenue CAGR 10%, PAT CAGR 10%
- Leverage: 15% — D/E 10%, ICR 5%

Each numeric metric is winsorised at the sector-level P10/P90 and scaled to 0–100. D/E is reverse-scaled because lower leverage is preferred. The resulting composite is bounded to 0–100.

Added `src/screener/composite.py` with sector-relative scoring, preset threshold masks, and `output/screener_output.xlsx` generation. The workbook is designed with one sheet per preset, 20 KPI columns, descending composite-score order, freeze panes, autofilter, and green/red threshold cell fills.

Day 17 scoring requires the complete metric set, including ROCE, FCF CAGR, CFO/PAT, valuation, dividend, sales, and net-profit fields. Missing inputs raise an explicit validation error rather than being fabricated.

**Validation status:** unit-test coverage was added, but full 92-company workbook generation requires running the scorer against the project's completed production dataset.


### Day 18 — Peer Percentile Rankings

Implemented `src/analytics/peer.py` for peer-group percentile analysis.

**Day 18 capabilities:**
- Loads `peer_groups.xlsx` from `data/raw/` (including prefixed workbook filenames).
- Builds unique company-to-peer-group membership and supports `peer_company_id` membership rows.
- Computes SQL-style `PERCENT_RANK` within each peer group and year for all 10 required metrics:
  ROE, ROCE, Net Profit Margin, D/E, FCF, PAT CAGR 5Y, Revenue CAGR 5Y, EPS CAGR 5Y, Interest Coverage, and Asset Turnover.
- Inverts D/E percentile as `1 - PERCENT_RANK`, so lower leverage receives a higher percentile.
- Populates the SQLite `peer_percentiles` table with:
  `company_id, peer_group_name, metric, value, percentile_rank, year`.
- Companies without a peer-group assignment are excluded from percentile calculation and reported as `No peer group assigned`; they do not raise an error.
- Added contract tests for percentile math, ties, D/E inversion, all ten metrics, and missing peer groups.

**Run:**

```bash
python -m src.analytics.peer --db db/nifty100.db --peer-groups data/raw
```

**Validation status:** implementation and contract tests are committed. Execute the command against the current production database/source workbook to verify the actual number of peer groups, percentile rows, and any unassigned companies.


### Day 19 — Radar Charts

Implemented `scripts/peer_reports.py` radar-chart generation using Matplotlib polar plots.

**Day 19 capabilities:**
- Generates one PNG per company with peer-group membership under `reports/radar_charts/`.
- Uses eight axes: ROE, ROCE, NPM, D/E, FCF Score, PAT CAGR 5Y, Revenue CAGR 5Y, and Composite Score.
- Normalizes axes to comparable 0–100 peer-relative scores; D/E is inverted so lower leverage scores higher.
- Shows the company as a filled polygon and the peer-group average as a dashed outline.
- Companies without a peer group receive a standalone Composite Score polar chart against the Nifty 100 average.
- Uses readable labels and 160 DPI PNG output.

Run:

```bash
python scripts/peer_reports.py --radar --db db/nifty100.db --peer-groups data/raw
```

### Day 20 — Peer Comparison Excel Report

The same reporting module generates `output/peer_comparison.xlsx`.

**Day 20 capabilities:**
- Requires and validates 11 peer groups.
- Creates one worksheet per peer group.
- Each sheet contains `company_id`, `company_name`, 10 raw peer metrics, and 10 percentile-rank columns.
- Percentile cells are green at >=75%, yellow from >25% to <75%, and red at <=25%.
- Highlights the benchmark row in amber/gold. If the source workbook contains an explicit benchmark column it is used; otherwise the first company in the group is used deterministically.
- Adds a peer-group median summary row for all numeric metric and percentile columns.
- Freezes headers, enables filters, and sizes columns for standard Excel viewing.

Run:

```bash
python scripts/peer_reports.py --excel --db db/nifty100.db --peer-groups data/raw
```

**Validation status:** Day 19/20 implementation and unit-test coverage are committed. Execute the commands against the current production database and source workbook before recording actual chart counts, workbook row counts, or final Sprint 3 sign-off.


### Day 21 — Automated Validation & Sprint 3 Review

Implemented the Day 21 Sprint 3 validation and review gate.

**Day 21 deliverables:**
- `scripts/day21_sprint_review.py` — automated Sprint 3 validation runner.
- `tests/sprint3/test_day21_sprint_review.py` — Day 21 contract tests.
- `docs/sprint3_review.md` — Sprint 3 review/report document.
- `.github/workflows/day21-validation.yml` — GitHub Actions validation workflow.
- `reports/radar_charts/` — radar-chart artifact directory containing the committed `HDFCBANK_radar.png` artifact and generation README.

**Automated validation covers:**
- ETL/data-quality test execution.
- Screener configuration availability.
- Quality Compounder sanity check.
- IT Services and FMCG peer-percentile spot checks.
- Exactly 11 peer groups and all 10 required peer metrics.
- Six-sheet screener workbook structure and per-preset row-count checks.
- Eleven-sheet peer-comparison workbook structure.
- Radar-chart artifact directory validation.
- Generation of `output/day21_sprint_review.md`.

**GitHub Actions:**

The workflow can be run manually from GitHub Actions or triggered by relevant repository changes. It installs Python dependencies, checks expected validation inputs, runs:

```bash
python scripts/day21_sprint_review.py --db db/nifty100.db
```

and uploads available review artifacts.

> **Validation note:** the Day 21 implementation and CI workflow are committed. Final 6/6 PASS status should be recorded only after executing the validator against the current production database and generated workbooks.


## Sprint 4 — Dashboard & Valuation Module

### Day 22 — Streamlit App Scaffold

Implemented the Sprint 4 dashboard foundation with an 8-screen Streamlit navigation shell.

**Day 22 deliverables:**
- `src/dashboard/app.py` — main Streamlit entry point.
- `src/dashboard/utils/db.py` — shared SQLite data-access helpers.
- Eight dashboard screens: Home, Profile, Screener, Peers, Trends, Sectors, Capital, and Reports.
- Streamlit page configuration: wide layout, title `Nifty 100 Analytics`, expanded sidebar.
- `streamlit` added to `requirements.txt`.

**Shared database helpers:**
- `get_companies()`
- `get_ratios(ticker, year=None)`
- `get_pl(ticker)`
- `get_bs(ticker)`
- `get_cf(ticker)`
- `get_sectors()`
- `get_peers(group_name)`
- `get_valuation(ticker)`

All dashboard query helpers use Streamlit's `@st.cache_data(ttl=600)` caching. The utilities return empty DataFrames with user-facing messages when the local database or optional tables are unavailable, so the dashboard scaffold can start without crashing on a missing generated database.

**Run locally:**

```bash
pip install -r requirements.txt
streamlit run src/dashboard/app.py
```

The expected local URL is `http://localhost:8501`.

> **Verification note:** Day 22 source files are committed. Final localhost/browser verification should be performed in an environment containing the generated `db/nifty100.db` and installed dependencies.


### Day 23 — Home Screen & Company Profile Screen

Implemented the Day 23 dashboard experience on top of the Day 22 Streamlit shell.

**Home screen:**
- Six KPI tiles: Average ROE, Median P/E, Median D/E, Total Companies, Median Revenue CAGR 5yr, and Debt-Free Companies.
- Plotly donut chart for sector breakdown.
- Top-5 companies by composite quality score.
- Metrics respond to the global 2019–2024 sidebar year selector.
- P/E is calculated from market cap / positive net profit when those source values are available.

**Company Profile:**
- Company/ticker search with a filtered autocomplete-style dropdown.
- Company card with name, sector, sub-sector/industry, NSE ticker, and database-backed About field with a transparent fallback when no description exists.
- Six selected-year KPI tiles: ROE, ROCE, Net Profit Margin, D/E, Revenue CAGR 5yr, and FCF.
- Plotly 10-year Revenue vs Net Profit bar chart.
- Plotly dual-axis ROE vs ROCE 10-year line chart.
- Pros/cons rendered with green check and red cross badges.
- Friendly Ticker not found message for unmatched searches.

**Additional Day 23 data helpers:**
- get_home_snapshot(year)
- get_profile_history(ticker)
- get_profile_pros_cons(ticker)
- Cached query helpers continue to use Streamlit cache_data with a 600-second TTL.

**Run locally:**

    pip install -r requirements.txt
    streamlit run src/dashboard/app.py

Then open http://localhost:8501 and use the sidebar year selector to test FY 2019–2024.
