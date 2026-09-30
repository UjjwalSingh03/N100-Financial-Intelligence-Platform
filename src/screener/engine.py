"""Config-driven financial screener for Sprint 3 Day 15.

The engine operates on a pandas DataFrame, normally loaded from the wide
financial_ratios table. Configuration is read from YAML and supports all
15 metrics required by the Sprint 3 specification.

Special rules:
* D/E filters are skipped for Financials companies.
* Debt Free ICR values are treated as infinity and therefore pass any minimum.
* Results are returned deterministically sorted by composite_quality_score.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import math
import pandas as pd
import yaml


METRIC_COLUMNS: dict[str, str] = {
    "roe_min": "return_on_equity_pct",
    "de_max": "debt_to_equity",
    "fcf_min": "free_cash_flow_cr",
    "revenue_cagr_5yr_min": "revenue_cagr_5yr",
    "pat_cagr_5yr_min": "pat_cagr_5yr",
    "opm_min": "operating_profit_margin_pct",
    "pe_max": "pe",
    "pb_max": "pb",
    "dividend_yield_min": "dividend_yield_pct",
    "icr_min": "interest_coverage",
    "market_cap_min": "market_cap",
    "net_profit_min": "net_profit",
    "eps_cagr_min": "eps_cagr_5yr",
    "asset_turnover_min": "asset_turnover",
    "sales_min": "sales",
    "dividend_payout_max": "dividend_payout_ratio_pct",
    "de_exact": "debt_to_equity",
    "revenue_cagr_3yr_min": "revenue_cagr_3yr",
    "de_trend": "debt_to_equity",
}

DEFAULT_CONFIG_PATH = Path("screener_config.yaml")


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load and validate the screener YAML configuration."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Screener config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    if not isinstance(config, dict):
        raise ValueError("Screener configuration must be a YAML mapping.")

    presets = config.get("presets", {})
    if not isinstance(presets, dict):
        raise ValueError("'presets' must be a mapping.")

    custom = config.get("custom", {})
    if custom is None:
        custom = {}
    if not isinstance(custom, dict):
        raise ValueError("'custom' must be a mapping.")

    return config


def _as_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _normalise_thresholds(thresholds: Mapping[str, Any] | None) -> dict[str, float]:
    """Validate threshold names and convert values to finite floats."""
    result: dict[str, float] = {}
    for name, value in (thresholds or {}).items():
        if name == "de_trend":
            if str(value).casefold() != "declining":
                raise ValueError("de_trend currently supports only 'declining'.")
            result[name] = str(value)
            continue
        if name not in METRIC_COLUMNS:
            raise ValueError(
                f"Unsupported screener filter '{name}'. "
                f"Supported filters: {', '.join(METRIC_COLUMNS)}"
            )
        numeric = _as_number(value)
        if numeric is None:
            raise ValueError(f"Filter '{name}' must have a finite numeric threshold.")
        result[name] = numeric
    return result


def _resolve_column(frame: pd.DataFrame, canonical: str) -> str:
    """Resolve a canonical metric to a DataFrame column using common aliases."""
    aliases = {
        "pe": ["pe", "p_e", "price_to_earnings"],
        "pb": ["pb", "p_b", "price_to_book"],
        "dividend_yield_pct": ["dividend_yield_pct", "dividend_yield"],
        "market_cap": ["market_cap", "market_cap_cr"],
        "net_profit": ["net_profit", "net_profit_cr"],
        "sales": ["sales", "revenue", "sales_cr"],
        "return_on_equity_pct": ["return_on_equity_pct", "roe", "roe_pct"],
        "debt_to_equity": ["debt_to_equity", "de"],
        "free_cash_flow_cr": ["free_cash_flow_cr", "free_cash_flow", "fcf"],
        "revenue_cagr_5yr": ["revenue_cagr_5yr", "revenue_cagr_5y"],
        "pat_cagr_5yr": ["pat_cagr_5yr", "pat_cagr_5y"],
        "operating_profit_margin_pct": ["operating_profit_margin_pct", "opm", "opm_pct"],
        "interest_coverage": ["interest_coverage", "icr"],
        "eps_cagr_5yr": ["eps_cagr_5yr", "eps_cagr_5y"],
        "asset_turnover": ["asset_turnover"],
    }
    candidates = aliases.get(canonical, [canonical])
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    raise KeyError(
        f"DataFrame is missing the column required for '{canonical}'. "
        f"Expected one of: {', '.join(candidates)}"
    )


def _sector_column(frame: pd.DataFrame) -> str | None:
    for name in ("broad_sector", "sector", "sector_name"):
        if name in frame.columns:
            return name
    return None


def _apply_minimum(frame: pd.DataFrame, column: str, threshold: float) -> pd.DataFrame:
    values = pd.to_numeric(frame[column], errors="coerce")
    return frame.loc[values >= threshold]


def _apply_maximum(frame: pd.DataFrame, column: str, threshold: float) -> pd.DataFrame:
    values = pd.to_numeric(frame[column], errors="coerce")
    return frame.loc[values <= threshold]


def apply_filters(
    data: pd.DataFrame,
    thresholds: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """Apply configured thresholds and return a sorted screener result.

    D/E is not evaluated for Financials rows. ICR missing values represent the
    Day 09 Debt Free case and are treated as infinity for minimum thresholds.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame")

    result = data.copy()
    filters = _normalise_thresholds(thresholds)

    if "composite_quality_score" not in result.columns:
        raise KeyError("financial_ratios data must contain composite_quality_score")

    sector_col = _sector_column(result)

    for filter_name, threshold in filters.items():
        canonical = METRIC_COLUMNS[filter_name]
        column = _resolve_column(result, canonical)

        if filter_name == "de_max":
            if sector_col is None:
                raise KeyError(
                    "D/E filtering requires a sector column ('broad_sector' or 'sector')."
                )
            financials = (
                result[sector_col].fillna("").astype(str).str.strip().str.casefold()
                == "financials"
            )
            non_financials = _apply_maximum(result.loc[~financials], column, threshold)
            financial_rows = result.loc[financials]
            result = pd.concat([non_financials, financial_rows], axis=0)
            continue

        if filter_name == "icr_min":
            values = pd.to_numeric(result[column], errors="coerce")
            result = result.loc[values.fillna(float("inf")) >= threshold]
            continue

        if filter_name == "dividend_payout_max":
            result = _apply_maximum(result, column, threshold)
        elif filter_name == "de_exact":
            values = pd.to_numeric(result[column], errors="coerce")
            result = result.loc[values == threshold]
        elif filter_name == "revenue_cagr_3yr_min":
            result = _apply_minimum(result, column, threshold)
        elif filter_name == "de_trend":
            if threshold != "declining":
                raise ValueError("de_trend currently supports only 'declining'.")
            if "company_id" not in result.columns or "year" not in result.columns:
                raise KeyError("D/E trend filtering requires company_id and year columns.")
            de = pd.to_numeric(result[column], errors="coerce")
            years = pd.to_numeric(result["year"].astype(str).str.extract(r"(\\d{4})")[0], errors="coerce")
            ordered = result.assign(_de=de, _year_num=years).sort_values(["company_id", "_year_num"])
            previous = ordered.groupby("company_id")["_de"].shift(1)
            keep = (previous.notna() & ordered["_de"].notna() & (ordered["_de"] < previous))
            result = ordered.loc[keep].drop(columns=["_de", "_year_num"])
        elif filter_name.endswith("_max"):
            result = _apply_maximum(result, column, threshold)
        else:
            result = _apply_minimum(result, column, threshold)

    sort_columns = ["composite_quality_score"]
    ascending = [False]
    if "company_id" in result.columns:
        sort_columns.append("company_id")
        ascending.append(True)
    if "year" in result.columns:
        sort_columns.append("year")
        ascending.append(False)

    return result.sort_values(
        sort_columns,
        ascending=ascending,
        kind="mergesort",
    ).reset_index(drop=True)


def apply_preset(
    data: pd.DataFrame,
    preset: str,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    *,
    overrides: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """Apply a named YAML preset, optionally overridden by custom thresholds."""
    config = load_config(config_path)
    presets = config.get("presets", {})
    if preset not in presets:
        available = ", ".join(sorted(presets))
        raise KeyError(f"Unknown preset '{preset}'. Available presets: {available}")

    thresholds = dict(presets[preset].get("filters", presets[preset]))
    if overrides:
        thresholds.update(overrides)
    return apply_filters(data, thresholds)


def apply_custom(
    data: pd.DataFrame,
    thresholds: Mapping[str, Any],
) -> pd.DataFrame:
    """Apply caller-provided custom thresholds without requiring YAML."""
    return apply_filters(data, thresholds)


def screen(
    data: pd.DataFrame,
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    preset: str | None = None,
    thresholds: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """Main Day 15 API for preset or custom screening."""
    if preset is not None:
        return apply_preset(data, preset, config_path, overrides=thresholds)
    if thresholds is None:
        config = load_config(config_path)
        thresholds = config.get("custom", {}).get("filters", {})
    return apply_filters(data, thresholds)
