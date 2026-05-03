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
