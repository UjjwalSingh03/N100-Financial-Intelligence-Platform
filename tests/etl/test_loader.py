from pathlib import Path

import pandas as pd
import pytest

from src.etl.loader import discover_workbooks, load_excel


def _write_bluestock_workbook(path: Path) -> None:
    frame = pd.DataFrame(
        [
            ["Bluestock Fintech — Nifty 100 | Test", None, None],
            ["id", "company_id", "year"],
            [1, "ABB", "Mar 2024"],
            [2, "TCS", "Mar 2024"],
            [None, None, None],
        ]
    )
    frame.to_excel(path, index=False, header=False)


def test_load_excel_detects_title_row(tmp_path):
    path = tmp_path / "profitandloss.xlsx"
    _write_bluestock_workbook(path)
    result = load_excel(path)
    assert list(result.columns) == ["id", "company_id", "year"]
    assert len(result) == 2
    assert result.loc[0, "company_id"] == "ABB"


def test_load_excel_removes_empty_rows_and_columns(tmp_path):
    path = tmp_path / "data.xlsx"
    pd.DataFrame([["id", "value", None], [1, 10, None], [None, None, None]]).to_excel(
        path, index=False, header=False
    )
    result = load_excel(path)
    assert list(result.columns) == ["id", "value"]
    assert len(result) == 1


def test_load_excel_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_excel(tmp_path / "missing.xlsx")


def test_load_excel_unsupported_extension_raises(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("id,value\n1,10\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_excel(path)


def test_discover_workbooks_returns_sorted_excel_files(tmp_path):
    for name in ["z.xlsx", "a.xlsx", "ignore.csv"]:
        (tmp_path / name).write_text("x", encoding="utf-8")
    paths = discover_workbooks(tmp_path)
    assert [p.name for p in paths] == ["a.xlsx", "z.xlsx"]
