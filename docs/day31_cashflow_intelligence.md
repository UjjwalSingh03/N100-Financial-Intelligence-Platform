# Day 31 — Cash Flow Intelligence Module

## Deliverables

Implemented in `src/analytics/cashflow_kpis.py`, reusing the Sprint 2 cash-flow calculations from `src/analytics/cash_flow.py`.

Run from the repository root:

```bash
python -m src.analytics.cashflow_kpis --db db/nifty100.db --output-dir output
```

The command generates:

- `output/cashflow_intelligence.xlsx`: one row per company with the requested 11 fields.
- `output/distress_alerts.csv`: only companies whose latest available cash-flow year has CFO < 0 and CFF > 0; includes CFO, CFF, and latest net profit.

## Calculation rules

- **CFO quality:** average of annual CFO/PAT ratios over the latest five common financial years. Years with missing CFO/PAT or zero PAT are skipped. Labels: >1.0 High Quality; 0.5–1.0 Moderate; <0.5 Accrual Risk. Missing valid history is labeled Insufficient Data.
- **CapEx intensity:** `abs(CFI) / sales * 100` for the latest available year. Labels: <3% Asset Light; 3–8% Moderate; >8% Capital Intensive.
- **FCF CAGR:** calculated only when positive FCF values exist at the beginning and end of a full five-year period. Otherwise left blank.
- **FCF conversion:** FCF divided by operating profit, multiplied by 100; undefined for missing or zero operating profit.
- **Distress:** latest CFO < 0 and CFF > 0.
- **Deleveraging:** latest CFF < 0 and latest available borrowings are lower than the previous available balance-sheet year.
- **Capital allocation:** classified from the latest CFO/CFI/CFF sign pattern, using the existing Sprint 2 classification helper.

The generator adapts to the normalized SQLite column names and handles missing tables/fields as unavailable data instead of inventing values. Verify the production outputs against the actual database before marking the full-company acceptance check as passed.

## Tests

Run:

```bash
pytest -q tests/analytics/test_cashflow_kpis.py tests/analytics/test_cash_flow.py
```
