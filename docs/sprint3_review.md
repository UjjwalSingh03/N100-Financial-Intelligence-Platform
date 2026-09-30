# Sprint 3 — Review & Retrospective

## Day 21 automated validation
Run: python scripts/day21_sprint_review.py --db db/nifty100.db

The validator checks DQ tests, the Quality Compounder ROE/D-E condition and top-five candidates, IT Services ROE percentile ordering, 11 peer groups and 10 peer metrics, six-sheet screener output, eleven-sheet peer output, and radar PNG artifacts. It exits non-zero when a required check fails or is blocked and writes output/day21_sprint_review.md.

## Definition of Done
- Six preset screeners each return 5–50 companies.
- screener_output.xlsx has six sheets.
- peer_comparison.xlsx has exactly 11 peer-group sheets.
- Peer percentile ranks are spot-checked for IT Services and FMCG.
- DQ tests pass with zero failures.
- Sprint review/demo is completed and signed off by the team lead.

The automated gate does not claim team-lead sign-off; that remains a human review action.

## Retrospective

### What went well
- Screener thresholds are configuration-driven and analyst-editable.
- Peer percentile computation is separated from reporting.
- Radar and Excel reports are reproducible from the database and peer workbook.
- Day 21 validation fails closed when production evidence is missing.

### What to improve
- Execute the full production pipeline before sprint review.
- Add FMCG to the automated percentile spot-check.
- Treat generated workbook/chart counts as execution evidence.
- Record team-lead sign-off separately from automated validation.

## Demo checklist
1. Show six screener sheets and manually review Quality Compounder top five.
2. Show IT Services and FMCG percentile spot-checks.
3. Open the 11 peer-group worksheets and demonstrate percentile colouring.
4. Open representative radar PNGs and explain the peer-average overlay.
5. Show the Day 21 validation report and test output.
6. Capture team-lead sign-off.

## Sprint 3 deliverables
- output/screener_output.xlsx
- output/peer_comparison.xlsx
- reports/radar_charts/
- peer_percentiles SQLite table
- config/screener_config.yaml (or the existing root screener_config.yaml)
- src/screener/engine.py
- src/analytics/peer.py
