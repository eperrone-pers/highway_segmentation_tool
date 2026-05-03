"""Pure helpers for zoom-related UI decisions."""

from __future__ import annotations

from typing import Optional, Tuple


def should_cache_default_limits(*, x_zoom_enabled: bool) -> bool:
    """Whether the segmentation plot should cache default x/y limits.

    Mirrors existing behavior: cache defaults only when X-zoom is OFF.
    """

    return not x_zoom_enabled


def normalize_xlim(xmin: float, xmax: float) -> Tuple[float, float]:
    """Return (min, max) for a possibly reversed xlim pair."""

    return (xmax, xmin) if xmax < xmin else (xmin, xmax)


def should_show_segmentation_paging_arrows(
    *,
    full_xlim: Optional[Tuple[float, float]],
    cur_xlim: Tuple[float, float],
    eps: float = 1e-9,
) -> bool:
    """Whether segmentation paging arrows should be visible.

    Mirrors existing UI behavior:
    - requires full_xlim
    - requires positive full span and current span
    - shows arrows only when zoomed in (current span < full span - eps)
    """

    if full_xlim is None:
        return False

    full_xmin, full_xmax = normalize_xlim(float(full_xlim[0]), float(full_xlim[1]))
    cur_xmin, cur_xmax = normalize_xlim(float(cur_xlim[0]), float(cur_xlim[1]))

    full_span = full_xmax - full_xmin
    cur_span = cur_xmax - cur_xmin
    if full_span <= 0 or cur_span <= 0:
        return False

    return cur_span < (full_span - eps)


def compute_paged_xlim(
    *,
    full_xlim: Optional[Tuple[float, float]],
    cur_xlim: Tuple[float, float],
    direction: int,
    eps: float = 1e-9,
) -> Optional[Tuple[float, float]]:
    """Compute the next paged x-window for segmentation.

    Returns:
    - None when paging is not applicable (missing full_xlim, invalid spans, or
      not zoomed in)
    - (new_xmin, new_xmax) clamped within full limits otherwise

    direction: -1 for left, +1 for right.
    """

    if full_xlim is None:
        return None

    full_xmin, full_xmax = normalize_xlim(float(full_xlim[0]), float(full_xlim[1]))
    cur_xmin, cur_xmax = normalize_xlim(float(cur_xlim[0]), float(cur_xlim[1]))

    span = cur_xmax - cur_xmin
    full_span = full_xmax - full_xmin
    if span <= 0 or full_span <= 0:
        return None

    # If not zoomed, nothing to page.
    if span >= full_span - eps:
        return None

    step = span if direction >= 0 else -span
    new_xmin = cur_xmin + step
    new_xmax = cur_xmax + step

    # Clamp at boundaries, preserving the window length.
    if new_xmin < full_xmin:
        new_xmin = full_xmin
        new_xmax = full_xmin + span
    if new_xmax > full_xmax:
        new_xmax = full_xmax
        new_xmin = full_xmax - span

    # Final safety: keep within bounds.
    if new_xmin < full_xmin:
        new_xmin = full_xmin
    if new_xmax > full_xmax:
        new_xmax = full_xmax

    return (new_xmin, new_xmax)
