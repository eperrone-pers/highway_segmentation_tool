"""Route identifier utilities.

This module centralizes route-id normalization rules so that route filtering,
optimization, export, and visualization all treat route identifiers the same.

A normalized route id is either:
- `None` (meaning "no route" / missing / invalid), or
- a stripped string value.

Important: This module intentionally avoids importing pandas/numpy/tkinter.
"""

from __future__ import annotations

import math
from typing import Any, Optional


# UI sentinel used in the route-column dropdown to indicate single-route mode.
# Centralized here so it is consistent across UI, controller, and visualization.
ROUTE_COLUMN_NONE_SENTINEL = "None - treat as single route"

# Internal/sentinel route IDs that should never be treated as real routes.
# Stored in lower-case for easy comparisons against normalized lower-case values.
INTERNAL_ROUTE_IDS_TO_SKIP_LOWER = {"_combined_data_"}


def normalize_route_id(value: Any) -> Optional[str]:
    """Normalize a route identifier to a stable string form.

    Rules:
    - `None` -> None
    - NaN-like values (float/numpy nan, pandas missing) -> None
    - Empty/whitespace-only strings -> None
    - Otherwise -> `str(value).strip()`

    Important: literal strings like "nan", "null", or "none" are treated as
    real route IDs if they appear in the input data.

    Args:
        value: Any route identifier (string, number, etc.).

    Returns:
        Normalized route id string, or None if the value is missing/invalid.
    """
    if value is None:
        return None

    # Treat numeric NaN / missing sentinel values as missing.
    # This preserves literal text values like "nan" (string) as data.
    try:
        if isinstance(value, (float, int)) and math.isnan(value):
            return None
    except Exception:
        pass

    # Catch numpy.nan and other NaN-like values (NaN != NaN).
    try:
        if value != value:  # noqa: PLR0124
            return None
    except Exception:
        # Some missing sentinels (e.g. pandas.NA) raise on truthiness/comparison.
        # Treat them as missing.
        return None

    route_str = str(value).strip()
    if not route_str:
        return None

    # pandas string dtype can surface missing values as the literal "<NA>"
    if route_str == "<NA>":
        return None

    return route_str


def filter_data_by_route(data, route_column: str, route_value: Any):
    """Filter a DataFrame to rows matching a specific route identifier.

    Route values are normalized before comparison to handle mixed types
    (e.g., integer 268296608 in data vs string "268296608" from the UI).

    Args:
        data: DataFrame with highway data.
        route_column: Name of the route column.
        route_value: Route identifier to filter by.

    Returns:
        Copy of rows where the route column matches route_value.
        Returns a full-DataFrame copy if route_column is absent, or an empty
        frame if route_value normalizes to None.
    """
    if route_column not in data.columns:
        return data.copy()

    route_str = normalize_route_id(route_value)
    if route_str is None:
        return data.iloc[0:0].copy()

    route_series = data[route_column].astype("string").str.strip()
    return data.loc[route_series == route_str].copy()


def list_routes(df, route_column: str) -> list:
    """Return sorted list of normalized, non-internal route IDs from df[route_column].

    Rows whose identifiers normalize to None (missing/invalid) and internal
    sentinel IDs (INTERNAL_ROUTE_IDS_TO_SKIP_LOWER) are silently excluded.

    Args:
        df: DataFrame containing a route column.
        route_column: Name of the column holding route identifiers.

    Returns:
        Sorted list of unique normalized route ID strings.
    """
    normalized = df[route_column].apply(normalize_route_id)
    routes = []
    for route_str in normalized.dropna():
        s = str(route_str)
        if s.lower() not in INTERNAL_ROUTE_IDS_TO_SKIP_LOWER:
            routes.append(s)
    return sorted(set(routes))


def normalize_route_column_selection(value: Any) -> Optional[str]:
    """Normalize a route column selection from the UI.

    The UI uses a sentinel label (ROUTE_COLUMN_NONE_SENTINEL) to represent
    "no route column" (single-route mode). This helper converts UI values to a
    stable internal representation.

    Rules:
    - None -> None
    - Empty/whitespace-only -> None
    - Exact match of ROUTE_COLUMN_NONE_SENTINEL -> None
    - Otherwise -> stripped string
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None
    if text == ROUTE_COLUMN_NONE_SENTINEL:
        return None
    return text
