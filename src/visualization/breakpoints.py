"""Pure helpers for breakpoint display decisions.

This module contains non-UI logic used by the enhanced visualization.
Matplotlib styling and drawing remain in `visualization_ui.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


def extract_mandatory_breakpoints(route_results: Optional[Dict[str, Any]]) -> Set[Any]:
    """Extract mandatory breakpoints from a route_results dict.

    Expected JSON path:
    - route_results.input_data_analysis.mandatory_segments.mandatory_breakpoints

    Missing or malformed values return an empty set.
    """

    if not route_results:
        return set()

    input_analysis = route_results.get("input_data_analysis")
    if not isinstance(input_analysis, dict):
        return set()

    mandatory_segments = input_analysis.get("mandatory_segments")
    if not isinstance(mandatory_segments, dict):
        return set()

    mandatory_breakpoints = mandatory_segments.get("mandatory_breakpoints") or []
    if not isinstance(mandatory_breakpoints, list):
        return set()

    return set(mandatory_breakpoints)


def add_endpoints_to_mandatory_breakpoints(
    mandatory_breakpoints: Iterable[Any],
    route_start: Optional[float],
    route_end: Optional[float],
) -> List[Any]:
    """Return sorted unique mandatory breakpoints including route endpoints.

    Mirrors the existing UI behavior: add start/end if not present, then
    `sorted(set(...))`.
    """

    bps = set(mandatory_breakpoints or [])
    if route_start is not None:
        bps.add(route_start)
    if route_end is not None:
        bps.add(route_end)
    return sorted(set(bps))


@dataclass(frozen=True)
class BreakpointLineSpec:
    x: float
    kind: str  # 'mandatory' | 'analysis'
    label: str


def compute_breakpoint_line_specs(
    breakpoints: Sequence[Any],
    mandatory_breakpoints: Iterable[Any],
    *,
    mandatory_label: str = "Mandatory Breakpoints",
    analysis_label: str = "Analysis Breakpoints",
) -> List[BreakpointLineSpec]:
    """Return line specs for rendering breakpoint vlines.

    Preserves the input breakpoint order.
    Includes each legend label at most once (first occurrence of each kind).
    """

    mandatory_raw: Set[Any] = set(mandatory_breakpoints or [])
    mandatory_numeric: Set[float] = set()
    for mbp in mandatory_raw:
        try:
            mandatory_numeric.add(float(mbp))
        except (TypeError, ValueError):
            continue

    specs: List[BreakpointLineSpec] = []
    mandatory_labeled = False
    analysis_labeled = False

    for bp in breakpoints or []:
        try:
            bp_x = float(bp)
        except (TypeError, ValueError):
            # Skip invalid breakpoint values rather than crashing matplotlib.
            continue

        is_mandatory = (bp in mandatory_raw) or (bp_x in mandatory_numeric)

        if is_mandatory:
            label = mandatory_label if not mandatory_labeled else ""
            mandatory_labeled = True
            specs.append(BreakpointLineSpec(x=bp_x, kind="mandatory", label=label))
        else:
            label = analysis_label if not analysis_labeled else ""
            analysis_labeled = True
            specs.append(BreakpointLineSpec(x=bp_x, kind="analysis", label=label))

    return specs


def split_breakpoints_by_mandatory(
    breakpoints: Sequence[float],
    mandatory_breakpoints: Iterable[float],
) -> Tuple[List[float], List[float]]:
    """Split breakpoints into mandatory and analysis lists.

    Preserves the input `breakpoints` order.

    Note: this intentionally does not coerce numeric types; it relies on Python's
    normal equality semantics (e.g., `1 == 1.0`).
    """

    mandatory_set: Set[float] = set(mandatory_breakpoints or [])

    mandatory: List[float] = []
    analysis: List[float] = []

    for bp in breakpoints or []:
        if bp in mandatory_set:
            mandatory.append(bp)
        else:
            analysis.append(bp)

    return mandatory, analysis


def xlim_from_breakpoints(breakpoints: Sequence[float]) -> Optional[Tuple[float, float]]:
    """Compute a usable x-axis range from breakpoint positions.

    Returns (min_bp, max_bp) when at least two breakpoints exist and sorting
    succeeds. Otherwise returns None.

    This mirrors the existing UI behavior (best-effort; never raise).
    """

    if not breakpoints or len(breakpoints) < 2:
        return None

    try:
        bp_sorted = sorted(breakpoints)
    except Exception:
        return None

    try:
        xmin = float(bp_sorted[0])
        xmax = float(bp_sorted[-1])
    except (TypeError, ValueError):
        return None

    return (xmin, xmax)
