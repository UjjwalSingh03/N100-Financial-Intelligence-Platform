# Dashboard Database Artifact

The Streamlit dashboard expects the SQLite database at:

`db/nifty100.db`

A verified dashboard-compatible database has been generated from the validated Sprint 3 database.

## Verified contents

- **92 companies**
- **1,177** profit-and-loss rows
- **1,227** balance-sheet rows
- **1,098** cash-flow rows
- **1,160** financial-ratio rows
- **552** market-cap rows
- **543** peer-percentile rows
- **1,457** annual-report document rows
- Ratio history through **2024**

The generated database also provides compatibility views/normalized year fields required by the current Streamlit dashboard.

## Install the generated DB locally

After downloading the verified SQLite file supplied with the project work:

1. Rename it to `nifty100.db`.
2. Copy it to the repository's `db/` directory.
3. Because `.gitignore` intentionally ignores SQLite binaries, use:

```bash
git add -f db/nifty100.db
git commit -m "data: add dashboard-compatible Nifty 100 SQLite database"
git push origin main
```

Then run:

```bash
python -m streamlit run src/dashboard/app.py
```

Open `http://localhost:8501`.

## Important

The SQLite binary is intentionally excluded from normal source-file commits by `.gitignore`. The `-f` flag is required when committing this dashboard artifact.
