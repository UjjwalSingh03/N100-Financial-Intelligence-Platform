# Sprint 5 — Retrospective and Review (Day 35)

## Scope
Day 29: structured analysis parser; Day 30: rule-based Pros/Cons; Day 31: cash-flow intelligence and distress alerts; Day 32: capital allocation audit and year-over-year changes; Day 33: two-page company tearsheet template; Day 34: company and sector batch reporting; Day 35: portfolio summary and exit audit.

## What went well
- Reusable analytics and report-generation modules are in place.
- Report outputs have deterministic locations and audit scripts.
- The capital-allocation source audit identified duplicate company/year keys and blank-year rows before downstream reporting.

## What needs improvement
- Production database and Excel source availability must be established before reporting completion.
- Batch outputs require PDF page-count, size, and visual checks; a successful script commit is not equivalent to validated delivery.
- Review generated Pros/Cons coverage and financial KPI completeness rather than assuming 92-company coverage.
- Standard Helvetica does not reliably render Unicode arrows; the portfolio uses explicit UP/DOWN/FLAT labels to avoid missing glyphs.

## Demo agenda for team lead
1. Show three sector-diverse company PDFs from reports/tearsheets (e.g., TCS, HDFCBANK, RELIANCE); verify both pages visually.
2. Open output/cashflow_intelligence.xlsx; inspect 92 rows and CFO quality, CapEx intensity, distress flags.
3. Open output/pros_cons_generated.csv; filter and verify at least one pro and one con per company.
4. Show reports/portfolio/portfolio_summary.pdf and sector report examples.
5. Review output/sprint5_exit_audit.csv and record any failed gates and corrective actions.

## Acceptance / sign-off
Run `python -m scripts.day35_portfolio_review` after Day 29–34 production generation, and inspect `output/sprint5_exit_audit.csv`. Also manually inspect five tearsheets for overflow, blank pages and chart rendering. A page-count/size check cannot substitute for visual review. Team lead meeting and approval remain **pending** until actually completed.

Team lead: __________________  Date: __________  Decision: __________
