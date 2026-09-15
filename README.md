# N100 Financial Intelligence Platform

A financial intelligence platform for Nifty 100 companies, covering data ingestion, validation, SQLite analytics, financial ratios, and reporting.

## Sprint 1 — Data Foundation

Day 01 establishes the project environment and repository structure. Later sprint days add Excel ingestion, normalization, data-quality validation, the SQLite schema, full data loading, exploratory SQL, and reporting.

## Project structure

```text
data/
  raw/          # Source Excel files
  processed/    # Cleaned/intermediate data

db/             # SQLite schema and database assets
notebooks/      # Exploratory SQL/notebooks
output/         # Generated reports and validation outputs
src/etl/        # ETL pipeline
tests/etl/      # ETL tests
```

## Setup

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and adjust local settings if required.
4. Put source Excel files in `data/raw/`.

## Day 01 commands

```bash
make test
make load
make clean
```

The loader is intentionally a Day 01 entry-point placeholder; Excel ingestion and normalization are implemented in Day 02.
