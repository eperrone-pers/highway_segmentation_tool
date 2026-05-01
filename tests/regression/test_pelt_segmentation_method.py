import pytest

from data_loader import analyze_route_gaps
from analysis.methods.pelt_segmentation import PeltSegmentationMethod


def _is_gap_segment(start: float, end: float, gap_segments) -> bool:
    tol = 1e-6
    for gap in gap_segments or []:
        if abs(float(start) - float(gap[0])) <= tol and abs(float(end) - float(gap[1])) <= tol:
            return True
    return False


@pytest.mark.regression
def test_pelt_segmentation_respects_mandatory_and_length_constraints(txdot_data):
    # Keep the test fast and deterministic-ish by slicing.
    df = txdot_data.head(800).copy()

    # Build gap-aware RouteAnalysis (same pipeline used by the GUI/controller).
    route_id = "TEST_PELT_SMOKE"
    gap_threshold = 0.5
    route_analysis = analyze_route_gaps(
        df,
        x_column="milepoint",
        y_column="structural_strength_ind",
        route_id=route_id,
        gap_threshold=gap_threshold,
    )

    method = PeltSegmentationMethod()

    # Settings tuned for a reasonable number of segments.
    # We assert invariants, not exact breakpoint values.
    min_length = 0.5
    max_length = 5.0
    result = method.run_analysis(
        route_analysis,
        route_id,
        x_column="milepoint",
        y_column="structural_strength_ind",
        gap_threshold=gap_threshold,
        model="l2",
        penalty=80.0,
        jump=1,
        smooth_window_miles=None,
        smoothing_method="mean",
        min_length=min_length,
        max_length=max_length,
        enable_diagnostic_output=False,
    )

    assert result.method_key == "pelt_segmentation"
    assert result.all_solutions and isinstance(result.all_solutions, list)

    breakpoints = result.best_solution.get("chromosome")
    assert isinstance(breakpoints, list)
    assert len(breakpoints) >= 2

    # Sorted unique and includes mandatory boundaries
    assert breakpoints == sorted(breakpoints)
    assert len(breakpoints) == len(set(breakpoints))

    mandatory = set(route_analysis.mandatory_breakpoints)
    assert mandatory.issubset(set(breakpoints))

    # Segment length checks
    gap_segments = getattr(route_analysis, "gap_segments", [])

    # Max-length should hold for ALL non-gap segments (including those touching mandatory bps)
    for start, end in zip(breakpoints, breakpoints[1:]):
        length = float(end) - float(start)
        if _is_gap_segment(start, end, gap_segments):
            continue
        assert length <= max_length + 1e-6

    # Min-length is enforced for non-gap segments that are not forced short by mandatory boundaries.
    for start, end in zip(breakpoints, breakpoints[1:]):
        length = float(end) - float(start)
        if _is_gap_segment(start, end, gap_segments):
            continue
        if start in mandatory or end in mandatory:
            continue
        assert length >= min_length - 1e-6
