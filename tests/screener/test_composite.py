"""Day 17 composite score tests."""

from __future__ import annotations

import pandas as pd
import pytest

from src.screener.composite import add_composite_quality_score


def frame() -> pd.DataFrame:
    rows = []
    for sector in ["Industrials", "Financials"]:
        for i in range(10):
            rows.append({
                "company_id": f"{sector[:2]}{i}",
                "year": 2025,
                "broad_sector": sector,
                "return_on_equity_pct": 10 + i,
                "return_on_capital_employed_pct": 8 + i,
                "net_profit_margin_pct": 5 + i,
                "fcf_cagr_5yr": 3 + i,
                "cfo_pat_ratio": 0.5 + i / 10,
                "fcf_positive_flag": 1 if i >= 2 else 0,
                "revenue_cagr_5yr": 4 + i,
                "pat_cagr_5yr": 5 + i,
                "debt_to_equity": 2 - i / 10,
                "interest_coverage": 2 + i,
            })
    return pd.DataFrame(rows)


def test_composite_score_is_bounded() -> None:
    result = add_composite_quality_score(frame())
    assert result["composite_quality_score"].between(0, 100).all()


def test_sector_relative_score_is_calculated() -> None:
    result = add_composite_quality_score(frame())
    assert result.groupby("broad_sector")["composite_quality_score"].count().to_dict() == {
        "Financials": 10,
        "Industrials": 10,
    }


def test_higher_quality_inputs_score_higher_within_sector() -> None:
    result = add_composite_quality_score(frame())
    industrials = result[result["broad_sector"] == "Industrials"].sort_values("company_id")
    assert industrials.iloc[-1]["composite_quality_score"] > industrials.iloc[0]["composite_quality_score"]


def test_missing_day17_metric_is_rejected() -> None:
    data = frame().drop(columns=["fcf_cagr_5yr"])
    with pytest.raises(KeyError, match="fcf_cagr_5yr"):
        add_composite_quality_score(data)
