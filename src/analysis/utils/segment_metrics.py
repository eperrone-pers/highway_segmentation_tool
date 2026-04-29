"""Segment-level metrics shared by analysis methods.

This module is intentionally method-owned/non-core: it provides helper functions
that methods can use to compute exported/reportable metrics without requiring the
results exporter to impose a single global definition.

Current project convention for shipped methods:
- "average_segment_length" should exclude *gap-only* segments (gap_start->gap_end).
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple, Union, Dict, Any


GapLike = Union[Tuple[float, float], Sequence[float], Dict[str, Any]]


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return float("nan")


def normalize_breakpoints(breakpoints: Sequence[float]) -> List[float]:
    """Return sorted float breakpoints with duplicates removed."""
    bps = []
    for x in breakpoints or []:
        try:
            bps.append(float(x))
        except Exception:
            continue
    bps = sorted(set(bps))
    return bps


def normalize_gap_segments(gap_segments: Iterable[GapLike]) -> List[Tuple[float, float]]:
    """Normalize gaps into a list of (start, end) float tuples.

    Accepts:
    - tuples/lists like (start, end)
    - dicts like {"start":..., "end":...}
    """
    normalized: List[Tuple[float, float]] = []
    for gap in gap_segments or []:
        if isinstance(gap, dict):
            start = _to_float(gap.get("start"))
            end = _to_float(gap.get("end"))
        else:
            try:
                start = _to_float(gap[0])  # type: ignore[index]
                end = _to_float(gap[1])  # type: ignore[index]
            except Exception:
                continue

        if start != start or end != end:  # NaN check
            continue
        normalized.append((float(start), float(end)))
    return normalized


def average_length_including_gaps(breakpoints: Sequence[float]) -> float:
    """Mean segment length over all consecutive breakpoint intervals."""
    bps = normalize_breakpoints(breakpoints)
    if len(bps) < 2:
        return 0.0

    lengths = []
    for a, b in zip(bps, bps[1:]):
        L = float(b - a)
        if L > 0:
            lengths.append(L)
    return float(sum(lengths) / len(lengths)) if lengths else 0.0


def average_length_excluding_gap_segments(
    breakpoints: Sequence[float],
    gap_segments: Iterable[GapLike],
    *,
    tolerance: float = 1e-9,
) -> float:
    """Mean segment length excluding segments that exactly match a detected gap.

    A segment is excluded only if (start,end) matches a gap boundary pair.
    Segments adjacent to gaps are included.
    """
    bps = normalize_breakpoints(breakpoints)
    if len(bps) < 2:
        return 0.0

    gaps = normalize_gap_segments(gap_segments)

    # Use a rounded lookup for speed and stability; still allow a tolerance.
    def key(x: float) -> float:
        # 9 dp is enough for milepoint-style values while keeping keys stable.
        return round(float(x), 9)

    gap_set = {(key(s), key(e)) for (s, e) in gaps}

    lengths = []
    for a, b in zip(bps, bps[1:]):
        L = float(b - a)
        if L <= 0:
            continue

        if gap_set:
            ka, kb = key(a), key(b)
            if (ka, kb) in gap_set:
                continue

            # Fallback tolerance check for non-rounded matches.
            # (Only used when needed; avoids O(n^2) scanning in the common case.)
            if tolerance and any(abs(a - gs) <= tolerance and abs(b - ge) <= tolerance for gs, ge in gaps):
                continue

        lengths.append(L)

    return float(sum(lengths) / len(lengths)) if lengths else 0.0
