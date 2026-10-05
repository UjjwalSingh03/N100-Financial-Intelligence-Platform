# Sprint 4 Retrospective — Dashboard & Valuation Module

## Scope

Sprint 4 covered Days 22–28: Streamlit dashboard, valuation analytics, integration QA, bug fixes, documentation, and demo preparation.

## UX decisions

- Used a single Streamlit entry point with sidebar navigation for all 8 screens.
- Kept the global financial-year selector in the sidebar so the dashboard shares the same year context.
- Used search + select controls for the 92-company universe where appropriate.
- Added friendly empty-state messages for missing data, missing history, missing reports, and unavailable metrics.
- Used responsive Plotly charts with container width for laptop and desktop layouts.
- Screener CSV export mirrors the visible result columns.
- Annual-report URLs are explicitly marked unavailable or unverified instead of being presented as confirmed.

## Data edge cases discovered

- The dashboard SQLite schema uses normalized aliases such as roe, de, and composite_score; pages must not assume raw source column names.
- The analysis table is a summary table and does not contain a year column, so the screener must not join it on year.
- P/E, P/B, and dividend yield are sourced from market_cap when available.
- Company identifiers are ticker strings; peer logic must not cast them to integers.
- The sector table exposes sub-sector classification as industry; the Sector screen uses that field for colour grouping.
- Cash-flow records can be incomplete; Capital Allocation includes a No Data category.
- Annual-report documents use id as the document key.
- Historical coverage can be shorter than ten years; Profile and Trends show available-history context.
- Optional valuation metrics can be NULL and are displayed as unavailable rather than fabricated.

## Performance findings

- Shared dashboard queries use Streamlit cache_data with a 600-second TTL.
- Day 27 added profile-load timing checks with a 3-second threshold.
- Plotly charts use responsive containers and compact margins.
- Final localhost/browser timing and interaction results must be taken from the local runtime; repository code alone does not prove a live browser result.

## Day 28 acceptance review

| Criterion | Repository status |
|---|---|
| 8-screen Streamlit application implemented | PASS — source files present |
| Cached dashboard data loader | PASS — src/dashboard/utils/db.py |
| Screener CSV implementation | PASS — download uses visible result columns |
| Valuation logic implemented | PASS — src/analytics/valuation.py |
| Valuation workbook contains 92 rows | PENDING — requires local valuation generation |
| Valuation flags CSV generated | PENDING — requires local valuation generation |
| All 8 screens load without errors for all 92 tickers | PENDING — requires local Streamlit/browser execution |
| Company Profile <3 seconds | PENDING — run scripts/day27_qa.py locally and confirm timings |
| Sprint 4 demo completed | PENDING — human team-lead demo required |
| Team-lead sign-off | PENDING — human approval required |

## Recommended final verification

```bash
python scripts/day27_qa.py
python -m src.analytics.valuation --db db/nifty100.db --market-cap data/raw --output-dir output
python -m streamlit run src/dashboard/app.py
```

Then walk through all 8 screens using representative companies from IT, Financials, FMCG, Energy, and Healthcare, verify the screener CSV, inspect the valuation outputs, and record team-lead sign-off separately.
