# Day 43 — Performance Notes

Status: **Benchmark implementation committed; production measurements pending.**

Run `python -m scripts.day43_performance` with the populated 92-company database. The runner overwrites this file with measured per-request timings, five profile data-load timings, SQLite query plans, and any execution errors.

## Baseline observations from source review

- Existing `db/schema.sql` already contains composite indexes for `profitandloss`, `balancesheet`, `cashflow`, `financial_ratios` and `market_cap` on `(company_id, year)`. Adding the same indexes again would be redundant.
- Day 43 adds missing company-scoped lookup indexes on analysis, documents, prosandcons, sectors, peer groups and peer percentile data.
- The screener currently builds latest KPI records across all companies and performs per-company lookups; this is a potential N+1 query bottleneck, **not yet a measured failure**. If the load test misses the 10-second target, profile it and replace repeated lookups with set-based SQL.
- The Company Profile uses multiple cached database helpers. The automated benchmark measures cold helper loading; visual page rendering requires a separate manual browser check.
- FastAPI and Streamlit use distinct ports (8000 and 8501). Simultaneous startup and data correctness are not yet verified on the production environment.

## Acceptance checklist

- [ ] Ten concurrent screener HTTP requests complete in under ten seconds total.
- [ ] Five selected ticker profile data loads each complete in under three seconds.
- [ ] Both processes start, both HTTP health checks pass and FastAPI reports 92 companies.
- [ ] Open the Streamlit UI, confirm screener data and profile data visually, and compare screener company IDs to API output under identical enabled filters.
- [ ] Review measured query plans and apply schema indexes to the **existing** database if necessary.

To apply new schema indexes to an existing DB, run a migration or execute the added `CREATE INDEX IF NOT EXISTS` statements explicitly; merely updating schema.sql does not change an already-created SQLite file.
