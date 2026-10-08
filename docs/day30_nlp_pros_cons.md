# Day 30 — NLP Auto Pros/Cons Generator

Implemented `src/nlp/pros_cons_generator.py`.

## Rules

The generator contains all 12 requested pro rules (`P01`–`P12`) and 12 con rules (`C01`–`C12`) covering ROE, FCF, leverage, growth, margins, PAT/EPS CAGR, ICR, dividends, ROCE, EBITDA leverage, and multi-year trends.

Each emitted signal receives a confidence score from 0–100. Only signals with `confidence_pct > 60` are written.

## Output

`output/pros_cons_generated.csv`

Columns:
- `company_id`
- `type`
- `rule_id`
- `text`
- `confidence_pct`

## Coverage validation

The default command uses strict coverage validation. It verifies that every company in `companies` has at least one generated pro and at least one generated con. Missing coverage raises an error instead of fabricating a statement.

For diagnostics only, incomplete coverage can be inspected with:

    python -m src.nlp.pros_cons_generator --db db/nifty100.db --output output/pros_cons_generated.csv --allow-incomplete-coverage

Production validation:

    python -m src.nlp.pros_cons_generator --db db/nifty100.db --output output/pros_cons_generated.csv

## Tests

Added `tests/nlp/test_pros_cons_generator.py` covering all 12 pro rules, all 12 con rules, confidence threshold, strict coverage failure behavior, and the output contract.

The production 92-company output should only be reported as verified after running the command against the actual `db/nifty100.db`.