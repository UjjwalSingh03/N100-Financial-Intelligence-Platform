"""Day 15 screener engine tests."""

from __future__ import annotations

import pandas as pd
import pytest

from src.screener.engine import apply_filters, apply_preset, load_config


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "company_id": "A", "year": 2025, "return_on_equity_pct": 20,
                "debt_to_equity": 0.5, "free_cash_flow_cr": 100,
                "revenue_cagr_5yr": 12, "pat_cagr_5yr": 14,
                "operating_profit_margin_pct": 18, "interest_coverage": 4,
                "asset_turnover": 1.5, "composite_quality_score": 80,
                "broad_sector": "Industrials",
            },
            {
                "company_id": "B", "year": 2025, "return_on_equity_pct": 18,
                "debt_to_equity": 12, "free_cash_flow_cr": 120,
                "revenue_cagr_5yr": 15, "pat_cagr_5yr": 11,
                "operating_profit_margin_pct": 20, "interest_coverage": None,
                "asset_turnover": 2, "composite_quality_score": 90,
                "broad_sector": "Financials",
            },
            {
                "company_id": "C", "year": 2025, "return_on_equity_pct": 10,
                "debt_to_equity": 0.2, "free_cash_flow_cr": 80,
                "revenue_cagr_5yr": 20, "pat_cagr_5yr": 20,
                "operating_profit_margin_pct": 25, "interest_coverage": 3,
                "asset_turnover": 2.5, "composite_quality_score": 95,
                "broad_sector": "Industrials",
            },
        ]
    )


def test_de_filter_skips_financials() -> None:
    result = apply_filters(sample_frame(), {"de_max": 1})
    assert set(result["company_id"]) == {"A", "B"}


def test_debt_free_icr_passes_any_minimum() -> None:
    result = apply_filters(sample_frame(), {"icr_min": 100})
    assert set(result["company_id"]) == {"B"}


def test_multiple_filters_are_combined() -> None:
    result = apply_filters(
        sample_frame(),
        {"roe_min": 15, "de_max": 1, "fcf_min": 90},
    )
    assert list(result["company_id"]) == ["B", "A"]


def test_results_are_sorted_by_composite_score() -> None:
    result = apply_filters(sample_frame(), {})
    assert list(result["company_id"]) == ["C", "B", "A"]


def test_unknown_filter_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported screener filter"):
        apply_filters(sample_frame(), {"unknown_min": 1})


def test_missing_metric_column_is_rejected() -> None:
    frame = sample_frame().drop(columns=["revenue_cagr_5yr"])
    with pytest.raises(KeyError, match="revenue_cagr_5yr"):
        apply_filters(frame, {"revenue_cagr_5yr_min": 10})


def test_yaml_presets_load() -> None:
    config = load_config()
    assert len(config["presets"]) == 6


def test_preset_and_override() -> None:
    result = apply_preset(sample_frame(), "quality", overrides={"roe_min": 19})
    assert list(result["company_id"]) == ["A"]
