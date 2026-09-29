"""Day 12 contract tests."""

from src.analytics.cagr import cagr_for_window
from scripts.populate_financial_ratios import KPI_COLUMNS, quality_score


def test_day12_has_all_required_kpis():
    assert len(KPI_COLUMNS) == 17
    assert "revenue_cagr_5yr" in KPI_COLUMNS
    assert "composite_quality_score" in KPI_COLUMNS


def test_day12_quality_score_is_bounded():
    score = quality_score(10, 15, 1, 3, 70)
    assert 0 <= score <= 100


def test_day12_five_year_cagr():
    values = [100, 105, 110, 115, 120, 161.051]
    assert cagr_for_window(values, 5).value == 10.0
