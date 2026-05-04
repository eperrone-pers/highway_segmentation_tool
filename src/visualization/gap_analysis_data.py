"""Pure helpers for working with input-data gap analysis.

This module isolates JSON-shape handling and the "show gap info once" decision.
UI code (printing/logging) remains in `visualization_ui.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


@dataclass(frozen=True)
class GapAnalysisInfo:
    gap_segments: List[Dict[str, Any]]
    total_gaps: int


def extract_gap_analysis(route_results: Optional[Dict[str, Any]]) -> GapAnalysisInfo:
    """Extract gap segments and total gap count from a route_results dict.

    Expected JSON path:
    - route_results.input_data_analysis.gap_analysis.gap_segments
    - route_results.input_data_analysis.gap_analysis.total_gaps

    Missing or malformed values return safe defaults.
    """

    if not route_results:
        return GapAnalysisInfo(gap_segments=[], total_gaps=0)

    input_analysis = route_results.get("input_data_analysis")
    if not isinstance(input_analysis, dict):
        return GapAnalysisInfo(gap_segments=[], total_gaps=0)

    gap_analysis = input_analysis.get("gap_analysis")
    if not isinstance(gap_analysis, dict):
        return GapAnalysisInfo(gap_segments=[], total_gaps=0)

    gap_segments = gap_analysis.get("gap_segments") or []
    if not isinstance(gap_segments, list):
        gap_segments = []

    total_gaps = gap_analysis.get("total_gaps", 0)
    try:
        total_gaps_int = int(total_gaps)
    except (TypeError, ValueError):
        total_gaps_int = 0

    return GapAnalysisInfo(gap_segments=gap_segments, total_gaps=total_gaps_int)


def should_show_gap_info_once(
    *,
    route_id: str,
    total_gaps: int,
    already_shown_routes: Optional[Iterable[str]],
) -> Tuple[bool, Set[str]]:
    """Return whether gap info should be shown and the updated shown-set.

    Behavior:
    - Only show if total_gaps > 0.
    - Only show once per route_id.
    - Always returns a (possibly new) set for the caller to store.
    """

    shown: Set[str] = set(already_shown_routes or [])

    if total_gaps <= 0:
        return False, shown

    if route_id in shown:
        return False, shown

    shown.add(route_id)
    return True, shown
