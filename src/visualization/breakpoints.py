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


def extract_gap_boundary_breakpoints(route_results: Optional[Dict[str, Any]]) -> Set[float]:
    """Extract gap boundary breakpoints (gap start/end) from a route_results dict.

    Expected JSON path:
    - route_results.input_data_analysis.gap_analysis.gap_segments[{start,end}]

    Missing or malformed values return an empty set.
    """

    if not route_results:
        return set()

    input_analysis = route_results.get("input_data_analysis")
    if not isinstance(input_analysis, dict):
        return set()

    gap_analysis = input_analysis.get("gap_analysis")
    if not isinstance(gap_analysis, dict):
        return set()

    gap_segments = gap_analysis.get("gap_segments") or []
    if not isinstance(gap_segments, list):
        return set()

    out: Set[float] = set()
    for seg in gap_segments:
        if not isinstance(seg, dict):
            continue
        for key in ("start", "end"):
            try:
                out.add(float(seg.get(key)))
            except (TypeError, ValueError):
                continue

    return out


def extract_attribute_breakpoints(route_results: Optional[Dict[str, Any]]) -> Set[float]:
    """Extract attribute-change breakpoint positions from a route_results dict.

    Expected JSON paths (optional):
    - route_results.input_data_analysis.attribute_break_analysis.breakpoints
    - route_results.input_data_analysis.attribute_break_analysis.break_events[{x,...}]
    - route_results.input_data_analysis.secondary_attribute_break_analysis.breakpoints
    - route_results.input_data_analysis.secondary_attribute_break_analysis.break_events[{x,...}]

    Missing or malformed values return an empty set.
    """

    if not route_results:
        return set()

    input_analysis = route_results.get("input_data_analysis")
    if not isinstance(input_analysis, dict):
        return set()

    out: Set[float] = set()

    # Extract from primary attribute breaks
    attr = input_analysis.get("attribute_break_analysis")
    if isinstance(attr, dict):
        breakpoints = attr.get("breakpoints")
        if isinstance(breakpoints, list):
            for bp in breakpoints:
                try:
                    out.add(float(bp))
                except (TypeError, ValueError):
                    continue

        events = attr.get("break_events")
        if isinstance(events, list):
            for e in events:
                if not isinstance(e, dict):
                    continue
                try:
                    out.add(float(e.get("x")))
                except (TypeError, ValueError):
                    continue

    # Extract from secondary attribute breaks
    secondary_attr = input_analysis.get("secondary_attribute_break_analysis")
    if isinstance(secondary_attr, dict):
        breakpoints = secondary_attr.get("breakpoints")
        if isinstance(breakpoints, list):
            for bp in breakpoints:
                try:
                    out.add(float(bp))
                except (TypeError, ValueError):
                    continue

        events = secondary_attr.get("break_events")
        if isinstance(events, list):
            for e in events:
                if not isinstance(e, dict):
                    continue
                try:
                    out.add(float(e.get("x")))
                except (TypeError, ValueError):
                    continue

    return out


def extract_attribute_break_signatures(route_results: Optional[Dict[str, Any]]) -> Dict[float, str]:
    """Extract a mapping of attribute-break x-position -> signature label.

    Expected JSON paths (optional):
    - route_results.input_data_analysis.attribute_break_analysis.break_events[{x,signature,changed_columns}]
    - route_results.input_data_analysis.secondary_attribute_break_analysis.break_events[{x,signature,changed_columns}]

    Uses `signature` when present; otherwise falls back to a joined changed_columns.
    Missing or malformed values return an empty dict.
    """

    if not route_results:
        return {}

    input_analysis = route_results.get("input_data_analysis")
    if not isinstance(input_analysis, dict):
        return {}

    out: Dict[float, str] = {}
    
    # Process primary attribute breaks
    attr = input_analysis.get("attribute_break_analysis")
    if isinstance(attr, dict):
        events = attr.get("break_events")
        if isinstance(events, list):
            for e in events:
                if not isinstance(e, dict):
                    continue

                try:
                    x = float(e.get("x"))
                except (TypeError, ValueError):
                    continue

                sig = e.get("signature")
                if sig is None:
                    changed = e.get("changed_columns")
                    if isinstance(changed, list):
                        sig = ", ".join([str(c).strip() for c in changed if str(c).strip()])

                sig = str(sig).strip() if sig is not None else ""
                if not sig:
                    continue

                out[x] = sig
    
    # Process secondary attribute breaks
    secondary_attr = input_analysis.get("secondary_attribute_break_analysis")
    if isinstance(secondary_attr, dict):
        events = secondary_attr.get("break_events")
        if isinstance(events, list):
            for e in events:
                if not isinstance(e, dict):
                    continue

                try:
                    x = float(e.get("x"))
                except (TypeError, ValueError):
                    continue

                sig = e.get("signature")
                if sig is None:
                    changed = e.get("changed_columns")
                    if isinstance(changed, list):
                        sig = ", ".join([str(c).strip() for c in changed if str(c).strip()])

                sig = str(sig).strip() if sig is not None else ""
                if not sig:
                    continue

                # If this x position already has a signature from primary, combine them
                if x in out:
                    out[x] = f"{out[x]}, {sig}"
                else:
                    out[x] = sig

    return out


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
    kind: str  # 'mandatory'|'analysis' or 'mandatory_gap'|'mandatory_attribute'|'mandatory_other'|'analysis'
    label: str


def compute_breakpoint_line_specs(
    breakpoints: Sequence[Any],
    mandatory_breakpoints: Iterable[Any],
    *,
    gap_breakpoints: Optional[Iterable[Any]] = None,
    attribute_breakpoints: Optional[Iterable[Any]] = None,
    mandatory_label: str = "Mandatory Breakpoints",
    gap_label: str = "Mandatory (Gaps)",
    attribute_label: str = "Mandatory (Attributes)",
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

    # Backward compatibility: if no cause information is provided, keep the
    # original two-kind behavior.
    use_causes = (gap_breakpoints is not None) or (attribute_breakpoints is not None)

    gap_numeric: Set[float] = set()
    attr_numeric: Set[float] = set()
    if use_causes:
        for gbp in (gap_breakpoints or []):
            try:
                gap_numeric.add(float(gbp))
            except (TypeError, ValueError):
                continue
        for abp in (attribute_breakpoints or []):
            try:
                attr_numeric.add(float(abp))
            except (TypeError, ValueError):
                continue

    specs: List[BreakpointLineSpec] = []
    mandatory_labeled = False
    gap_labeled = False
    attribute_labeled = False
    analysis_labeled = False

    for bp in breakpoints or []:
        try:
            bp_x = float(bp)
        except (TypeError, ValueError):
            # Skip invalid breakpoint values rather than crashing matplotlib.
            continue

        is_mandatory = (bp in mandatory_raw) or (bp_x in mandatory_numeric)

        if not is_mandatory:
            label = analysis_label if not analysis_labeled else ""
            analysis_labeled = True
            specs.append(BreakpointLineSpec(x=bp_x, kind="analysis", label=label))
            continue

        if not use_causes:
            label = mandatory_label if not mandatory_labeled else ""
            mandatory_labeled = True
            specs.append(BreakpointLineSpec(x=bp_x, kind="mandatory", label=label))
            continue

        # With cause info: classify mandatory breakpoints.
        if bp_x in gap_numeric:
            label = gap_label if not gap_labeled else ""
            gap_labeled = True
            specs.append(BreakpointLineSpec(x=bp_x, kind="mandatory_gap", label=label))
        elif bp_x in attr_numeric:
            label = attribute_label if not attribute_labeled else ""
            attribute_labeled = True
            specs.append(BreakpointLineSpec(x=bp_x, kind="mandatory_attribute", label=label))
        else:
            # Keep endpoints/other mandatory lines unlabeled unless there are
            # no cause-specific labels available.
            if (not gap_numeric) and (not attr_numeric):
                label = mandatory_label if not mandatory_labeled else ""
                mandatory_labeled = True
            else:
                label = ""
            specs.append(BreakpointLineSpec(x=bp_x, kind="mandatory_other", label=label))

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
