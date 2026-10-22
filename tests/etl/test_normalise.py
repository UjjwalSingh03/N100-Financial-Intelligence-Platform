"""Twenty normalization cases: year formats, boundaries and invalid inputs."""
import pandas as pd
import pytest
from src.etl.normaliser import normalize_year

@pytest.mark.parametrize("raw,expected", [
    (2024,2024),(2024.0,2024),("2024",2024),(" FY2024 ",2024),
    ("FY24",2024),("FY 24",2024),("2023-24",2024),("2023/24",2024),
    ("FY2023-24",2024),("Mar 2024",2024),("Mar-24",2024),
    (pd.Timestamp("2024-03-31"),2024),(1900,1900),(2100,2100),
    (1899,None),(2101,None),(None,None),(pd.NA,None),("",None),("not-a-year",None),
])
def test_normalize_year(raw, expected):
    assert normalize_year(raw) == expected
