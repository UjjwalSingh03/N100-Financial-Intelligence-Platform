"""Day 17 composite quality scoring and Excel export.

Scoring is sector-relative: each component is winsorised at P10/P90 within
broad_sector and linearly scaled to 0-100. Higher-is-better metrics are used
directly; D/E is inverted and ICR is capped before scaling.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Any

import numpy as np
import pandas as pd


COMPONENTS = {
    "profitability": {
        "return_on_equity_pct": 0.15,
        "return_on_capital_employed_pct": 0.10,
        "net_profit_margin_pct": 0.10,
    },
    "cash_quality": {
        "fcf_cagr_5yr": 0.15,
        "cfo_pat_ratio": 0.10,
        "fcf_positive_flag": 0.05,
    },
    "growth": {
        "revenue_cagr_5yr": 0.10,
        "pat_cagr_5yr": 0.10,
    },
    "leverage": {
        "debt_to_equity": 0.10,
        "interest_coverage": 0.05,
    },
}


def _required(frame: pd.DataFrame, columns: list[str]) -> None:
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise KeyError("Day 17 composite scoring requires columns: " + ", ".join(missing))


def _winsor_scale(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    valid = values.dropna()
    if valid.empty:
        return pd.Series(np.nan, index=series.index)
    p10, p90 = valid.quantile([0.10, 0.90])
    if p90 <= p10:
        scaled = pd.Series(50.0, index=series.index)
    else:
        capped = values.clip(lower=p10, upper=p90)
        scaled = (capped - p10) / (p90 - p10) * 100
    if not higher_is_better:
        scaled = 100 - scaled
    return scaled


def sector_relative_scores(
    data: pd.DataFrame,
    *,
    sector_column: str = "broad_sector",
) -> pd.DataFrame:
    """Return input plus sector-relative 0-100 component metric columns."""
    required = [sector_column] + [c for group in COMPONENTS.values() for c in group]
    _required(data, required)
    result = data.copy()

    directions = {"debt_to_equity": False}
    for metric in [c for group in COMPONENTS.values() for c in group]:
        if metric == "fcf_positive_flag":
            values = pd.to_numeric(result[metric], errors="coerce").fillna(0)
            result[f"_score_{metric}"] = values.clip(0, 1) * 100
            continue
        result[f"_score_{metric}"] = (
            result.groupby(sector_column, dropna=False)[metric]
            .transform(lambda s: _winsor_scale(s, directions.get(metric, True)))
        )
    return result


def add_composite_quality_score(data: pd.DataFrame) -> pd.DataFrame:
    """Compute 0-100 sector-relative composite score using the Day 17 weights."""
    result = sector_relative_scores(data)
    result["profitability_score"] = sum(
        result[f"_score_{metric}"] * weight
        for metric, weight in COMPONENTS["profitability"].items()
    )
    result["cash_quality_score"] = sum(
        result[f"_score_{metric}"] * weight
        for metric, weight in COMPONENTS["cash_quality"].items()
    )
    result["growth_score"] = sum(
        result[f"_score_{metric}"] * weight
        for metric, weight in COMPONENTS["growth"].items()
    )
    result["leverage_score"] = sum(
        result[f"_score_{metric}"] * weight
        for metric, weight in COMPONENTS["leverage"].items()
    )
    result["composite_quality_score"] = (
        result["profitability_score"]
        + result["cash_quality_score"]
        + result["growth_score"]
        + result["leverage_score"]
    ).clip(0, 100)
    return result.drop(columns=[c for c in result.columns if c.startswith("_score_")])


def threshold_mask(data: pd.DataFrame, thresholds: Mapping[str, Any]) -> pd.DataFrame:
    """Return one boolean column per preset threshold for Excel formatting."""
    from .engine import METRIC_COLUMNS, _resolve_column

    out = pd.DataFrame(index=data.index)
    for name, threshold in thresholds.items():
        if name in {"de_trend"}:
            out[name] = True
            continue
        if name == "de_exact":
            col = _resolve_column(data, METRIC_COLUMNS[name])
            out[name] = pd.to_numeric(data[col], errors="coerce") == float(threshold)
        elif name.endswith("_max"):
            col = _resolve_column(data, METRIC_COLUMNS[name])
            out[name] = pd.to_numeric(data[col], errors="coerce") <= float(threshold)
        else:
            col = _resolve_column(data, METRIC_COLUMNS[name])
            out[name] = pd.to_numeric(data[col], errors="coerce") >= float(threshold)
    return out


def export_preset_workbook(
    data: pd.DataFrame,
    config: Mapping[str, Any],
    output_path: str | Path = "output/screener_output.xlsx",
    *,
    kpi_columns: list[str] | None = None,
) -> Path:
    """Export one sheet per preset with threshold-based green/red formatting."""
    from openpyxl import load_workbook
    from openpyxl.styles import PatternFill
    from .engine import apply_preset

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    presets = config.get("presets", {})
    if not presets:
        raise ValueError("No screener presets configured.")

    enriched = add_composite_quality_score(data)
    default_kpis = [
        "company_id", "year", "broad_sector", "composite_quality_score",
        "return_on_equity_pct", "return_on_capital_employed_pct",
        "net_profit_margin_pct", "fcf_cagr_5yr", "cfo_pat_ratio",
        "fcf_positive_flag", "revenue_cagr_5yr", "pat_cagr_5yr",
        "debt_to_equity", "interest_coverage", "free_cash_flow_cr",
        "sales", "net_profit", "pe", "pb", "dividend_yield_pct",
    ]
    columns = kpi_columns or default_kpis
    _required(enriched, columns)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for preset_name, preset in presets.items():
            result = apply_preset(enriched, preset_name)
            result = result.sort_values("composite_quality_score", ascending=False)
            result[columns].to_excel(writer, sheet_name=preset_name[:31], index=False)

    workbook = load_workbook(output)
    green = PatternFill(fill_type="solid", fgColor="C6EFCE")
    red = PatternFill(fill_type="solid", fgColor="FFC7CE")

    for preset_name, preset in presets.items():
        sheet = workbook[preset_name[:31]]
        result = apply_preset(enriched, preset_name).sort_values(
            "composite_quality_score", ascending=False
        ).reset_index(drop=True)
        masks = threshold_mask(result, preset.get("filters", {}))
        for col_idx, name in enumerate(columns, start=1):
            if name not in masks.columns:
                continue
            for row_idx, passes in enumerate(masks[name].tolist(), start=2):
                sheet.cell(row=row_idx, column=col_idx).fill = green if passes else red
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for column_cells in sheet.columns:
            width = min(max(len(str(cell.value or "")) for cell in column_cells) + 2, 28)
            sheet.column_dimensions[column_cells[0].column_letter].width = width

    workbook.save(output)
    return output
