"""Excel ingestion helpers for Sprint 1 Day 02.

The loader reads Excel workbooks from ``data/raw`` and provides a small,
consistent ingestion API. Normalisation rules live in ``normaliser.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"


def load_excel(path: str | Path, *, sheet_name: str | int = 0) -> pd.DataFrame:
    """Load one Excel worksheet into a DataFrame with blank rows removed."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Excel source not found: {source}")
    if source.suffix.lower() not in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        raise ValueError(f"Unsupported Excel file type: {source.suffix}")

    df = pd.read_excel(source, sheet_name=sheet_name, engine="openpyxl")
    df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")
    df.columns = [str(column).strip() for column in df.columns]
    return df.reset_index(drop=True)


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
        if path.is_file() and path.suffix.lower() in {".xlsx", ".xlsm", ".xltx", ".xltm"}
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
