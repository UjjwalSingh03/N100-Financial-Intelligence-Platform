from __future__ import annotations

import pandas as pd

from src.analytics.valuation import _add_valuation_flags


def test_valuation_flag_thresholds_use_latest_year_sector_median():
    frame = pd.DataFrame(
        [
            {"company_id": "A", "sector": "IT", "year": 2023, "P/E": 20.0},
            {"company_id": "B", "sector": "IT", "year": 2023, "P/E": 10.0},
            {"company_id": "C", "sector": "IT", "year": 2023, "P/E": 5.0},
            {"company_id": "A", "sector": "IT", "year": 2024, "P/E": 30.0},
            {"company_id": "B", "sector": "IT", "year": 2024, "P/E": 20.0},
            {"company_id": "C", "sector": "IT", "year": 2024, "P/E": 10.0},
        ]
    )

    result = _add_valuation_flags(frame)
    latest = result[result["year"] == 2024].set_index("company_id")

    # Latest-year sector median = 20.
    assert latest.loc["A", "flag"] == "Fair"
    assert latest.loc["B", "flag"] == "Fair"
    assert latest.loc["C", "flag"] == "Discount"
    assert latest.loc["A", "PE_vs_sector_median_pct"] == 50.0

    # A's five-year median uses the available historical P/E values.
    assert latest.loc["A", "5yr_median_PE"] == 25.0
