"""Value parsing and coercion utilities.

This module centralizes small parsing rules that are used in multiple places
(GUI widgets, settings persistence, config parameter definitions).

Keep this module free of tkinter/pandas/numpy imports so it is safe to use in
core logic and tests.
"""

from __future__ import annotations

import math
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


def parse_optional_float(value: Any) -> Optional[float]:
    """Parse an optional numeric value as float.

    Missing policy is delegated to `coerce_none_like()`:
    - None / empty / "(None)" / "null" / "none" -> None
    - All other values are preserved and then parsed as float

    Important: This rejects numeric NaN values (including the string "nan" after
    float conversion). The string "nan" is not treated as missing; it's treated
    as invalid numeric input.
    """
    coerced = coerce_none_like(value)
    if coerced is None:
        return None

    parsed = float(coerced)
    if math.isnan(parsed):
        raise ValueError("NaN is not a valid numeric value")
    return parsed


def parse_optional_int(value: Any) -> Optional[int]:
    """Parse an optional numeric value as int.

    Same missing policy as `parse_optional_float()`. Raises ValueError if the
    value is not an integer.
    """
    parsed = parse_optional_float(value)
    if parsed is None:
        return None
    if not float(parsed).is_integer():
        raise ValueError("Value must be an integer")
    return int(parsed)
