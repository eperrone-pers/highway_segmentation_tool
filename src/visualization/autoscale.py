"""Pure helpers for computing y-limits in a visible x-window.

This module intentionally contains both:
- selecting visible y-values for an x-range, and
- turning those y-values into padded y-axis limits.

Matplotlib rendering remains in `visualization_ui.py`.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

import numpy as np

from visualization.zoom_decisions import normalize_xlim


def visible_y_values_in_x_window(
    x_values: Sequence[float],
    y_values: Sequence[float],
    *,
    xmin: float,
    xmax: float,
) -> Optional[np.ndarray]:
    """Return y-values whose corresponding x-values fall within [xmin, xmax].

    Mirrors existing segmentation zoom logic:
    - returns None when inputs are empty/mismatched or when no points are visible
    - accepts reversed windows (xmin > xmax)
    """

    try:
        x = np.asarray(x_values)
        y = np.asarray(y_values)
    except Exception:
        return None

    if x.size == 0 or y.size == 0:
        return None

    if x.shape[0] != y.shape[0]:
        return None

    xmin, xmax = normalize_xlim(float(xmin), float(xmax))

    mask = (x >= xmin) & (x <= xmax)
    if not np.any(mask):
        return None

    return y[mask]


def autoscale_y_limits(
    y_values: Sequence[float],
    *,
    pad_fraction: float = 0.05,
    min_pad: float = 1.0,
) -> Optional[Tuple[float, float]]:
    """Compute y-axis limits with padding.

    Mirrors the existing segmentation autoscale behavior:
    - ignores NaN/inf
    - returns None when no finite values
    - padding = (y_max - y_min) * pad_fraction
    - if padding is 0, use min_pad
    """

    y = np.asarray(y_values, dtype=float)
    if y.size == 0:
        return None

    y = y[np.isfinite(y)]
    if y.size == 0:
        return None

    y_min = float(np.nanmin(y))
    y_max = float(np.nanmax(y))

    if not (np.isfinite(y_min) and np.isfinite(y_max)):
        return None
    if y_max < y_min:
        return None

    pad = (y_max - y_min) * float(pad_fraction)
    if pad == 0:
        pad = float(min_pad)

    return (y_min - pad, y_max + pad)
