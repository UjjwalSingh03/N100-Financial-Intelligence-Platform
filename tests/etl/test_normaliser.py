import pandas as pd
import pytest

from src.etl.normaliser import normalize_ticker, normalize_year


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (2024, 2024),
        (2024.0, 2024),
        ("2024", 2024),
        (" FY2024 ", 2024),
        ("FY24", 2024),
        ("2023-24", 2024),
        ("2023/24", 2024),
        ("FY2023-24", 2024),
        ("FY 2023/24", 2024),
        ("2023", 2023),
        (pd.Timestamp("2022-03-31"), 2022),
        ("31-Mar-2025", 2025),
        ("2021-12-31", 2021),
        (None, None),
        ("", None),
        ("not-a-year", None),
        (1899, None),
        (2200, None),
        (True, None),
        (pd.NaT, None),
    ],
)
def test_normalize_year(value, expected):
    assert normalize_year(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("RELIANCE", "RELIANCE"),
        (" reliance ", "RELIANCE"),
        ("Reliance", "RELIANCE"),
        ("NSE:RELIANCE", "RELIANCE"),
        ("BSE:500325", "500325"),
        ("TCS.NS", "TCS"),
        ("INFY.BO", "INFY"),
        ("  HDFCBANK  ", "HDFCBANK"),
        ("HDFC BANK", "HDFCBANK"),
        ("itc", "ITC"),
        ("ABC-", "ABC"),
        ("ABC_", "ABC"),
        ("ABC/", "ABC"),
        (None, None),
        ("", None),
        ("   ", None),
        (pd.NA, None),
        ("nse:TCS.ns", "TCS"),
    ],
)
def test_normalize_ticker(value, expected):
    assert normalize_ticker(value) == expected


def test_normalize_ticker_is_deterministic():
    value = "  nse:reliance.ns  "
    assert normalize_ticker(value) == normalize_ticker(value) == "RELIANCE"
