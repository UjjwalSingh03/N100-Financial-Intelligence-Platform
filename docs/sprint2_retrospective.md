# Sprint 2 Retrospective — Financial Ratio Engine

## Formula decisions
- Profitability uses normalized financial-statement inputs for NPM, OPM, ROE, ROCE and ROA.
- D/E uses borrowings / (equity capital + reserves); Financials are excluded from the generic high-leverage warning.
- ICR uses (operating profit + other income) / interest; zero interest is undefined/debt-free.
- CAGR handles sign changes, zero bases and insufficient history with explicit flags.
- FCF is CFO + CFI and may be negative; FCF conversion is FCF / operating profit.
- Capital allocation uses the documented CFO/CFI/CFF sign taxonomy.

## Edge-case resolutions
- Non-positive equity/assets and zero denominators return undefined values rather than misleading ratios.
- TURNAROUND, DECLINE_TO_LOSS, BOTH_NEGATIVE, ZERO_BASE and INSUFFICIENT are explicit CAGR states.
- Source ROCE/ROE are reference values; ratio-engine values remain authoritative for analytics.
- Financials leverage warnings are suppressed by design.
- Every anomaly in ratio_edge_cases.log must have a category and explanation before sign-off.

## Review evidence
The Day 14 runner records formula-test count, financial_ratios row count, null-only KPI columns, FK status, screener count, edge-log documentation and capital-allocation output.

## Sign-off
Team-lead sign-off is an external review step and must be recorded after the validation runner succeeds and the five-company KPI demo is presented.
