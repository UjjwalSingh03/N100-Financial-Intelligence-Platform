# Sprint 1 Source Excel Inputs

Place the 12 logical source workbooks in this directory before running the ETL.
Do not rename the logical datasets because downstream table mapping uses these names.

1. `companies.xlsx` — company master; primary identifier is `id` (ticker).
2. `profitandloss.xlsx` — P&L history; `company_id` references `companies.id`.
3. `balancesheet.xlsx` — balance-sheet history; equity is represented by `equity_capital + reserves`.
4. `cashflow.xlsx` — cash-flow history.
5. `analysis.xlsx` — analysis records.
6. `documents.xlsx` — annual-report/document URLs.
7. `prosandcons.xlsx` — qualitative pros/cons.
8. `sectors.xlsx` — sector classification.
9. `stock_prices.xlsx` — daily OHLC/adjusted-close prices.
10. `financial_ratios.xlsx` — annual financial ratios.
11. `market_cap.xlsx` — annual market-cap and valuation data.
12. `peer_groups.xlsx` — peer-group membership.

The supplied Bluestock workbooks may contain a descriptive title row before the
real header. `src/etl/loader.py` detects the actual header automatically.

Excel files are intentionally not committed by default because the repository
`.gitignore` is designed to keep source data and generated databases out of Git.
