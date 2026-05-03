"""Pure data preparation helpers for segmentation plotting.

These functions intentionally avoid any matplotlib/UI dependencies so they can be
unit tested independently. The rendering (axes calls, colors, labels) remains in
`visualization_ui.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np


GapInterval = Tuple[float, float]
SegmentInterval = Tuple[float, float]


@dataclass(frozen=True)
class SegmentAverageLine:
    start_x: float
    end_x: float
    avg_y: float
    label: str = ""


def preprocess_gap_intervals(gap_segments: Optional[Iterable[dict]]) -> List[GapInterval]:
    """Convert raw gap dicts into sorted (start, end) float intervals.

    A gap is considered valid if:
    - start and end are both present (not None)
    - start < end

    Invalid gaps are ignored.
    """

    if not gap_segments:
        return []

    intervals: List[GapInterval] = []
    for gap in gap_segments:
        if not isinstance(gap, dict):
            continue

        start = gap.get("start")
        end = gap.get("end")

        if start is None or end is None:
            continue

        try:
            start_f = float(start)
            end_f = float(end)
        except (TypeError, ValueError):
            continue

        if start_f < end_f:
            intervals.append((start_f, end_f))

    return sorted(intervals)


def segments_outside_gaps(segments: Sequence[SegmentInterval], gap_intervals: Sequence[GapInterval]) -> List[SegmentInterval]:
    """Filter segments to those that do not overlap any gap interval.

    Overlap condition matches the existing UI logic: a segment overlaps a gap if
    it is NOT fully before or after the gap.
    """

    if not gap_intervals:
        return list(segments)

    valid_segments: List[SegmentInterval] = []

    for seg_start, seg_end in segments:
        overlaps = False

        for gap_start, gap_end in gap_intervals:
            # Early termination: if gap starts after segment ends, remaining gaps
            # (sorted) can't overlap.
            if gap_start >= seg_end:
                break

            if seg_end > gap_start and seg_start < gap_end:
                overlaps = True
                break

        if not overlaps:
            valid_segments.append((seg_start, seg_end))

    return valid_segments


def compute_segment_average_lines(
    *,
    x_data: np.ndarray,
    y_data: np.ndarray,
    breakpoints: Sequence[float],
    gap_segments: Optional[Iterable[dict]] = None,
) -> List[SegmentAverageLine]:
    """Compute horizontal average lines for segments defined by breakpoints.

    This matches the current visualization behavior:
    - segments are formed as consecutive pairs of sorted breakpoints
    - segments that overlap any gap are excluded
    - within each valid segment, use points where start <= x <= end
    - if there are points, compute avg(y) and return a line for that segment
    """

    if breakpoints is None or len(breakpoints) < 2:
        return []

    sorted_breakpoints = sorted(breakpoints)
    segments: List[SegmentInterval] = [
        (sorted_breakpoints[i], sorted_breakpoints[i + 1]) for i in range(len(sorted_breakpoints) - 1)
    ]

    gap_intervals = preprocess_gap_intervals(gap_segments)
    valid_segments = segments_outside_gaps(segments, gap_intervals)

    lines: List[SegmentAverageLine] = []
    labeled = False

    for start_bp, end_bp in valid_segments:
        segment_mask = (x_data >= start_bp) & (x_data <= end_bp)
        if not np.any(segment_mask):
            continue

        segment_y = y_data[segment_mask]
        if len(segment_y) <= 0:
            continue

        avg_y = float(np.mean(segment_y))
        label = "Segment Averages" if not labeled else ""
        labeled = True
        lines.append(
            SegmentAverageLine(
                start_x=float(start_bp),
                end_x=float(end_bp),
                avg_y=avg_y,
                label=label,
            )
        )

    return lines
