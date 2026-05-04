"""Route identifier utilities.

This module centralizes route-id normalization rules so that route filtering,
optimization, export, and visualization all treat route identifiers the same.

A normalized route id is either:
- `None` (meaning "no route" / missing / invalid), or
- a stripped string value.

Important: This module intentionally avoids importing pandas/numpy/tkinter.
"""

from __future__ import annotations

from typing import Any, Optional


# UI sentinel used in the route-column dropdown to indicate single-route mode.
# Centralized here so it is consistent across UI, controller, and visualization.
ROUTE_COLUMN_NONE_SENTINEL = "None - treat as single route"

# When scanning a route column, missing values are currently promoted to a
# visible route bucket in the UI.
MISSING_ROUTE_DISPLAY_LABEL = "Default"

# Internal/sentinel route IDs that should never be treated as real routes.
# Stored in lower-case for easy comparisons against normalized lower-case values.
INTERNAL_ROUTE_IDS_TO_SKIP_LOWER = {"default", "_combined_data_"}


_MISSING_ROUTE_STRINGS = {"nan", "none", "null"}


def normalize_route_id(value: Any) -> Optional[str]:
    """Normalize a route identifier to a stable string form.

    Rules (kept consistent with existing controller behavior):
    - `None` -> None
    - Empty/whitespace-only -> None
    - Case-insensitive values in {"nan", "none", "null"} -> None
    - Otherwise -> `str(value).strip()`

    Args:
        value: Any route identifier (string, number, etc.).

    Returns:
        Normalized route id string, or None if the value is missing/invalid.
    """
    if value is None:
        return None

    route_str = str(value).strip()
    if not route_str:
        return None

    if route_str.lower() in _MISSING_ROUTE_STRINGS:
        return None

    return route_str


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
