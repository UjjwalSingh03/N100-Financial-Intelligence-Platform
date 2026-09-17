"""Excel ingestion helpers for Sprint 1 Day 02.

The supplied Bluestock workbooks contain a title row before the real column
header in several files.  This loader detects that header row instead of
assuming row 1 is the schema, then removes empty rows/columns and normalises
column names without changing source values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
EXCEL_EXTENSIONS = {".xlsx", ".xlsm", ".xltx", ".xltm"}


def _find_header_row(raw: pd.DataFrame) -> int:
    """Find the real header row in a Bluestock-style workbook.

    Most source files have a descriptive title in row 1 and the schema in
    row 2.  Some already start with the schema.  We detect a row containing
    ``id`` and, where applicable, ``company_id``/``year``.
    """
    for row_number in range(min(len(raw), 15)):
        values = {str(v).strip().lower() for v in raw.iloc[row_number].tolist() if pd.notna(v)}
        if "id" in values and ("company_id" in values or "company_name" in values or "peer_group_name" in values):
            return row_number
        if {"id", "company_id", "year"}.issubset(values):
            return row_number
    return 0


def _clean_columns(columns: Iterable[object]) -> list[str]:
    """Strip column whitespace and discard Excel's accidental unnamed labels."""
    cleaned: list[str] = []
    for column in columns:
        name = str(column).strip()
        cleaned.append(name)
    return cleaned


def load_excel(path: str | Path, *, sheet_name: str | int = 0) -> pd.DataFrame:
    """Load one Excel worksheet and detect a title row when present."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Excel source not found: {source}")
    if source.suffix.lower() not in EXCEL_EXTENSIONS:
        raise ValueError(f"Unsupported Excel file type: {source.suffix}")

    raw = pd.read_excel(source, sheet_name=sheet_name, header=None, engine="openpyxl")
    header_row = _find_header_row(raw)
    df = raw.iloc[header_row + 1 :].copy()
    df.columns = _clean_columns(raw.iloc[header_row].tolist())
    df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")
    df = df.reset_index(drop=True)
    return df


def load_workbooks(paths: Iterable[str | Path]) -> dict[str, pd.DataFrame]:
    """Load multiple workbooks, keyed by their filename stem."""
    return {Path(path).stem: load_excel(path) for path in paths}


def discover_workbooks(raw_dir: str | Path = RAW_DATA_DIR) -> list[Path]:
    """Return Excel workbooks in deterministic filename order."""
    directory = Path(raw_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in EXCEL_EXTENSIONS
    )


def main() -> None:
    """Load all discovered Excel files and report their dimensions."""
    workbooks = discover_workbooks()
    if not workbooks:
        print(f"No Excel workbooks found in {RAW_DATA_DIR}")
        return

    for path in workbooks:
        frame = load_excel(path)
        print(f"{path.name}: {len(frame)} rows x {len(frame.columns)} columns")


if __name__ == "__main__":
    main()
