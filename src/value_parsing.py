"""Value parsing and coercion utilities.

This module centralizes small parsing rules that are used in multiple places
(GUI widgets, settings persistence, config parameter definitions).

Keep this module free of tkinter/pandas/numpy imports so it is safe to use in
core logic and tests.
"""

from __future__ import annotations

from typing import Any, Optional, Union


_NONE_LIKE_STRINGS = {"none", "(none)", "null"}


def coerce_none_like(value: Any) -> Any:
    """Coerce common "none-like" values to `None`.

    Behavior (intentionally narrow and stable):
    - `None` stays `None`
    - Strings are stripped; if empty or case-insensitive in {"none", "(none)", "null"}
      then return `None`
    - All other values are returned unchanged

    Note: This function does NOT treat "nan" as None, because doing so can hide
    invalid numeric input (e.g. float('nan')).
    """
    if value is None:
        return None

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if stripped.lower() in _NONE_LIKE_STRINGS:
            return None
        return stripped

    return value


def coerce_optional_numeric_text(text: Union[str, None]) -> Optional[str]:
    """Coerce optional-numeric widget text to either None or a stripped string."""
    return coerce_none_like(text)  # type: ignore[return-value]
