"""Normalisation utilities for Excel financial data."""

from __future__ import annotations

import re
from numbers import Integral, Real

import pandas as pd


def normalize_year(value: object) -> int | None:
    """Normalize common financial-year representations to a four-digit year.

    Examples accepted include ``2024``, ``"2024"``, ``"FY2024"``,
    ``"FY24"``, ``"2023-24"``, ``"2023/24"``, and date-like values.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)) or pd.isna(value):
        return None

    if isinstance(value, Integral) and not isinstance(value, bool):
        year = int(value)
        return year if 1900 <= year <= 2100 else None

    if isinstance(value, Real) and not isinstance(value, bool):
        number = float(value)
        if number.is_integer() and 1900 <= number <= 2100:
            return int(number)

    if isinstance(value, (pd.Timestamp,)):
        return int(value.year)

    text = str(value).strip().upper()
    if not text:
        return None

    # Exact four-digit calendar year.
    match = re.fullmatch(r"(?:FY\s*)?(19\d{2}|20\d{2}|21\d{2})", text)
    if match:
        return int(match.group(1))

    # Financial-year notation such as 2023-24 / FY23-24: use ending year.
    match = re.fullmatch(r"FY?\s*(\d{2}|20\d{2})\s*[-/]\s*(\d{2}|20\d{2})", text)
    if match:
        end = int(match.group(2))
        return 2000 + end if end < 100 else end

    # Excel/date strings: parse only when the result is a sensible year.
    parsed = pd.to_datetime(text, errors="coerce")
    if not pd.isna(parsed) and 1900 <= parsed.year <= 2100:
        return int(parsed.year)

    return None


def normalize_ticker(value: object) -> str | None:
    """Normalize an exchange ticker to uppercase, whitespace-free text."""
    if value is None or pd.isna(value):
        return None

    ticker = str(value).strip().upper()
    if not ticker:
        return None

    ticker = ticker.replace("NSE:", "").replace("BSE:", "")
    ticker = re.sub(r"\s+", "", ticker)
    ticker = ticker.replace(".NS", "").replace(".BO", "")
    ticker = ticker.strip(".-_/")

    return ticker or None
