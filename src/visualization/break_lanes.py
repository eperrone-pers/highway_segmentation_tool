"""Helpers for rendering attribute break lanes.

This module is UI-agnostic: it computes per-attribute lane boxes (start/end/value)
that a plotting layer can render.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence


@dataclass(frozen=True)
class LaneBox:
    start_x: float
    end_x: float
    value: str


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def attribute_breakpoints_by_column(
    attribute_break_analysis: Optional[Dict[str, Any]],
) -> Dict[str, List[float]]:
    """Return {column_name: sorted unique break x positions}.

    Uses `break_events` and their `changed_columns` list.
    Returns empty dict when missing/malformed.
    """

    if not isinstance(attribute_break_analysis, dict):
        return {}

    events = attribute_break_analysis.get("break_events")
    if not isinstance(events, list):
        return {}

    out: Dict[str, set] = {}

    for e in events:
        if not isinstance(e, dict):
            continue

        x = _to_float(e.get("x"))
        if x is None:
            continue

        changed = e.get("changed_columns")
        if not isinstance(changed, list):
            continue

        for c in changed:
            name = str(c).strip()
            if not name:
                continue
            out.setdefault(name, set()).add(x)

    return {k: sorted(v) for k, v in out.items()}


def _nearest_index(x_values: Sequence[float], x_target: float) -> Optional[int]:
    if not x_values:
        return None

    best_i = None
    best_dist = None
    for i, x in enumerate(x_values):
        try:
            d = abs(float(x) - float(x_target))
        except Exception:
            continue
        if best_dist is None or d < best_dist:
            best_dist = d
            best_i = i

    return best_i


def compute_lane_boxes(
    *,
    x_values: Sequence[float],
    attribute_values: Sequence[Any],
    lane_breakpoints: Iterable[float],
    x_min: float,
    x_max: float,
) -> List[LaneBox]:
    """Compute contiguous lane boxes between breakpoints.

    Picks the attribute value from the nearest x-row to each interval midpoint.
    """

    # Normalize and include endpoints
    bps = [float(b) for b in (lane_breakpoints or []) if _to_float(b) is not None]
    bps.extend([float(x_min), float(x_max)])

    bps_sorted = sorted(set(bps))
    if len(bps_sorted) < 2:
        return []

    boxes: List[LaneBox] = []

    # Pre-coerce x_values into floats for stable distance checks.
    x_vals_f: List[float] = []
    for x in x_values:
        xf = _to_float(x)
        x_vals_f.append(xf if xf is not None else float("nan"))

    for start, end in zip(bps_sorted, bps_sorted[1:]):
        if end <= start:
            continue

        mid = (start + end) / 2.0
        idx = _nearest_index(x_vals_f, mid)
        if idx is None or idx >= len(attribute_values):
            val = ""
        else:
            raw = attribute_values[idx]
            if raw is None:
                val = ""
            else:
                s = str(raw)
                val = "" if s.lower() == "nan" else s

        boxes.append(LaneBox(start_x=float(start), end_x=float(end), value=val))

    return boxes
