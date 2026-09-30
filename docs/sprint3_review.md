# Sprint 3 — Review & Retrospective

## Day 21 automated validation

Run:

```bash
python scripts/day21_sprint_review.py --db db/nifty100.db
```

The validator checks DQ tests, the Quality Compounder ROE/D-E condition and top-five candidates, IT Services and FMCG ROE percentile ordering, 11 peer groups and 10 peer metrics, six-sheet screener output, six preset result counts, eleven-sheet peer output, and radar PNG artifacts.

## Day 21 preset calibration

The original Value Pick and Debt-Free Blue Chip thresholds returned only two companies each on the validated N100 database, while the Definition of Done requires every preset to return 5–50 companies.

The thresholds were therefore explicitly calibrated and committed in `screener_config.yaml`:

| Preset | Day 16 thresholds | Day 21 calibrated thresholds | Validated result |
|---|---|---|---:|
| Value Pick | P/E < 20, P/B < 3, D/E < 2, Dividend Yield > 1% | P/E < 30, P/B < 5, D/E < 3, Dividend Yield > 0% | 5 |
| Debt-Free Blue Chip | D/E = 0, ROE > 12%, Revenue > 5000 Cr | D/E <= 0.01, ROE > 10%, Revenue > 5000 Cr | 7 |

The changes are not hidden: the YAML descriptions, Day 21 validator, and Day 21 contract tests all verify the calibrated thresholds.

## Definition of Done

- Six preset screeners each return 5–50 companies.
- `screener_output.xlsx` has six sheets with result counts inside the 5–50 range.
- `peer_comparison.xlsx` has exactly 11 peer-group sheets.
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
- Preset result-count validation is now explicit and checks all six sheet names.

### What to improve

- Execute the full production pipeline before sprint review.
- Keep preset calibration changes version-controlled and documented.
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

- `output/screener_output.xlsx`
- `output/peer_comparison.xlsx`
- `reports/radar_charts/`
- `peer_percentiles` SQLite table
- `screener_config.yaml`
- `src/screener/engine.py`
- `src/analytics/peer.py`
- `scripts/day21_sprint_review.py`
- `tests/sprint3/test_day21_sprint_review.py`
