"""Normalisation utilities for the supplied N100 Excel data."""

from __future__ import annotations

import re
from numbers import Integral, Real

import pandas as pd


def normalize_year(value: object) -> int | None:
    """Normalize calendar/FY values to the ending four-digit financial year.

    Examples: 2024, ``FY2024``, ``FY24``, ``2023-24``, ``Mar 2024`` and
    ``2023/24`` all resolve to an integer year. Invalid or missing values
    return ``None``.
    """
    if value is None or value is pd.NaT or value is pd.NA:
        return None
    if isinstance(value, (float, Real)) and not isinstance(value, bool) and pd.isna(value):
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

    match = re.fullmatch(r"FY\s*(19\d{2}|20\d{2}|21\d{2})", text)
    if match:
        return int(match.group(1))

    match = re.fullmatch(r"(19\d{2}|20\d{2}|21\d{2})", text)
    if match:
        return int(match.group(1))

    # Indian financial-year notation: 2023-24 means FY ending in 2024.
    match = re.fullmatch(r"(?:FY\s*)?(\d{2}|19\d{2}|20\d{2}|21\d{2})\s*[-/]\s*(\d{2}|19\d{2}|20\d{2}|21\d{2})", text)
    if match:
        end = int(match.group(2))
        return 2000 + end if end < 100 else end

    parsed = pd.to_datetime(text, errors="coerce")
    if not pd.isna(parsed) and 1900 <= parsed.year <= 2100:
        return int(parsed.year)
    return None


def normalize_ticker(value: object) -> str | None:
    """Normalize NSE/BSE ticker text without altering the identifier itself."""
    if value is None or value is pd.NA:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None

    ticker = str(value).strip().upper()
    if not ticker:
        return None

    ticker = re.sub(r"^(NSE|BSE)\s*:\s*", "", ticker)
    ticker = re.sub(r"\.(NS|BO)$", "", ticker)
    ticker = re.sub(r"\s+", "", ticker)
    ticker = ticker.strip(".-_/")
    return ticker or None
