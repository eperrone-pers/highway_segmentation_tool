"""Unit tests for the Invalid Data Handler preprocessing method."""

import math
import os
import sys

import pandas as pd
import pytest

current_file_dir = os.path.dirname(__file__)
tests_dir = os.path.dirname(current_file_dir)
project_root = os.path.dirname(tests_dir)
src_path = os.path.join(project_root, "src")

if src_path not in sys.path:
    sys.path.insert(0, src_path)

from data_loader import analyze_route_gaps
from preprocessing.methods.invalid_data_handler import InvalidDataHandlerPreprocessor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

X_COL = "milepoint"
Y_COL = "value"


def _make_route_analysis(x_vals, y_vals):
    """Build a RouteAnalysis from parallel x/y lists (NaN allowed in y_vals)."""
    df = pd.DataFrame({X_COL: x_vals, Y_COL: y_vals})
    return analyze_route_gaps(df, X_COL, Y_COL, route_id="TEST", gap_threshold=5.0)


def _run(route_analysis, **params):
    preprocessor = InvalidDataHandlerPreprocessor()
    return preprocessor.process(route_analysis, X_COL, Y_COL, log_callback=None, **params)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_nan_y_is_noop():
    """Method returns immediately when no NaN-Y rows are present."""
    ra = _make_route_analysis(range(10), range(10))
    result = _run(ra, y_strategy="drop")

    assert result.modification_log == []
    assert len(result.processed_route_analysis.route_data) == 10
    assert result.preprocessing_metadata["nan_y_count"] == 0


@pytest.mark.unit
def test_drop_strategy_removes_nan_rows():
    """Drop strategy removes all NaN-Y rows and logs each as point_removed."""
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [1.0, float("nan"), 3.0, float("nan"), 5.0]
    ra = _make_route_analysis(x, y)
    result = _run(ra, y_strategy="drop")

    df_out = result.processed_route_analysis.route_data
    assert len(df_out) == 3
    assert df_out[Y_COL].isna().sum() == 0

    removed = [m for m in result.modification_log if m.modification_type == "point_removed"]
    assert len(removed) == 2
    removed_x = {m.x_value for m in removed}
    assert removed_x == {1.0, 3.0}


@pytest.mark.unit
def test_moving_average_replaces_nan():
    """Moving average strategy imputes NaN-Y with neighbors' mean (window_size=1 → 1 per side)."""
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [2.0, float("nan"), 4.0, float("nan"), 6.0]
    ra = _make_route_analysis(x, y)
    result = _run(ra, y_strategy="moving_average", window_size=1)

    df_out = result.processed_route_analysis.route_data
    assert df_out[Y_COL].isna().sum() == 0

    # x=1: 1 valid left neighbor (2.0), 1 valid right neighbor (4.0) → mean = 3.0
    row_1 = df_out.loc[df_out[X_COL] == 1.0, Y_COL].iloc[0]
    assert math.isclose(row_1, 3.0, rel_tol=1e-6)

    # x=3: 1 valid left neighbor (4.0), 1 valid right neighbor (6.0) → mean = 5.0
    row_3 = df_out.loc[df_out[X_COL] == 3.0, Y_COL].iloc[0]
    assert math.isclose(row_3, 5.0, rel_tol=1e-6)

    imputed = [m for m in result.modification_log if m.modification_type == "y_value_changed"]
    assert len(imputed) == 2


@pytest.mark.unit
def test_moving_average_drops_when_entire_route_is_nan():
    """When all Y values are NaN, moving_average finds no valid neighbors and falls back to drop.
    Mandatory breakpoints (route start/end) are skipped; non-mandatory rows are dropped."""
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [float("nan")] * 5
    ra = _make_route_analysis(x, y)
    result = _run(ra, y_strategy="moving_average", window_size=1)

    removed = [m for m in result.modification_log if m.modification_type == "point_removed"]
    removed_x = {m.x_value for m in removed}
    # Non-mandatory interior rows are dropped; x=0.0 and x=4.0 are mandatory and skipped
    assert removed_x == {1.0, 2.0, 3.0}


@pytest.mark.unit
def test_linear_interpolate_imputes_nan():
    """Linear interpolate strategy computes correct intermediate values."""
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [0.0, float("nan"), float("nan"), 3.0, 4.0]
    ra = _make_route_analysis(x, y)
    result = _run(ra, y_strategy="linear_interpolate")

    df_out = result.processed_route_analysis.route_data
    assert df_out[Y_COL].isna().sum() == 0

    # x=1: between (0, 0.0) and (3, 3.0) → t=1/3 → y=1.0
    row_1 = df_out.loc[df_out[X_COL] == 1.0, Y_COL].iloc[0]
    assert math.isclose(row_1, 1.0, rel_tol=1e-6)

    # x=2: between (0, 0.0) and (3, 3.0) → t=2/3 → y=2.0
    row_2 = df_out.loc[df_out[X_COL] == 2.0, Y_COL].iloc[0]
    assert math.isclose(row_2, 2.0, rel_tol=1e-6)

    imputed = [m for m in result.modification_log if m.modification_type == "point_interpolated"]
    assert len(imputed) == 2


@pytest.mark.unit
def test_linear_interpolate_drops_when_no_left_neighbor():
    """NaN with no valid left neighbor (non-mandatory point) falls back to drop."""
    # x=1.0 has NaN Y; x=0.0 also has NaN Y so there is no valid left neighbor.
    # x=1.0 is not a mandatory breakpoint so it can be dropped.
    # x=0.0 is a mandatory breakpoint (route start) so it is skipped even though NaN.
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [float("nan"), float("nan"), 3.0, 4.0, 5.0]
    ra = _make_route_analysis(x, y)
    result = _run(ra, y_strategy="linear_interpolate")

    # x=1.0 (no valid left) → dropped; x=0.0 (mandatory) → skipped
    removed = [m for m in result.modification_log if m.modification_type == "point_removed"]
    assert any(m.x_value == 1.0 for m in removed)
    assert not any(m.x_value == 0.0 for m in removed)


@pytest.mark.unit
def test_threshold_raises_when_exceeded():
    """When enable_threshold is True and bad fraction > threshold_percent, raises ValueError."""
    x = list(range(10))
    y = [float("nan")] * 5 + [1.0] * 5  # 50% bad
    ra = _make_route_analysis(x, y)

    with pytest.raises(ValueError, match="exceeding the configured threshold"):
        _run(ra, y_strategy="drop", enable_threshold=True, threshold_percent=10.0)


@pytest.mark.unit
def test_threshold_disabled_does_not_raise():
    """When enable_threshold is False, high bad-row fraction does not raise."""
    x = list(range(10))
    y = [float("nan")] * 8 + [1.0, 2.0]  # 80% bad; last two valid so endpoints are non-NaN
    ra = _make_route_analysis(x, y)

    result = _run(ra, y_strategy="drop", enable_threshold=False, threshold_percent=10.0)
    assert result.preprocessing_metadata["nan_y_count"] == 8


@pytest.mark.unit
def test_all_nan_y_drop_removes_non_mandatory_rows():
    """All NaN-Y rows + drop strategy — mandatory breakpoints (route start/end) are skipped."""
    # x=0.0 and x=4.0 are mandatory (route start/end); x=1,2,3 can be dropped.
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [float("nan")] * 5
    ra = _make_route_analysis(x, y)
    result = _run(ra, y_strategy="drop")

    # Only mandatory points remain (x=0.0 and x=4.0 could not be removed)
    removed = [m for m in result.modification_log if m.modification_type == "point_removed"]
    assert len(removed) == 3  # x=1, 2, 3 dropped
    assert all(m.x_value in {1.0, 2.0, 3.0} for m in removed)


@pytest.mark.unit
def test_drop_skips_mandatory_breakpoint_with_nan():
    """NaN at a mandatory breakpoint is never dropped — the point is left in place."""
    # x=0.0 is mandatory (route start); it has NaN but must survive
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [float("nan"), 1.0, 2.0, 3.0, 4.0]
    ra = _make_route_analysis(x, y)
    result = _run(ra, y_strategy="drop")

    df_out = result.processed_route_analysis.route_data
    # x=0.0 still present even though its Y is NaN
    assert 0.0 in df_out[X_COL].values
    removed_x = {m.x_value for m in result.modification_log if m.modification_type == "point_removed"}
    assert 0.0 not in removed_x


@pytest.mark.unit
def test_moving_average_imputes_mandatory_breakpoint_with_valid_neighbors():
    """NaN at a mandatory breakpoint IS imputed when valid neighbors exist.

    Mandatory protection only prevents the drop fallback — if neighbors are
    available the strategy still fixes the NaN so the route is usable.
    """
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [float("nan"), 1.0, 2.0, 3.0, 4.0]
    ra = _make_route_analysis(x, y)
    result = _run(ra, y_strategy="moving_average", window_size=2)

    df_out = result.processed_route_analysis.route_data
    # mandatory breakpoint is still present and now has a valid Y
    assert 0.0 in df_out[X_COL].values
    imputed_x = {m.x_value for m in result.modification_log if m.modification_type == "y_value_changed"}
    assert 0.0 in imputed_x


@pytest.mark.unit
def test_moving_average_keeps_mandatory_breakpoint_when_no_neighbors():
    """NaN at a mandatory breakpoint with no valid neighbors is NOT dropped."""
    # x=0.0 mandatory (route start), NaN Y, no left neighbor, right neighbors all NaN
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [float("nan")] * 5
    ra = _make_route_analysis(x, y)
    result = _run(ra, y_strategy="moving_average", window_size=1)

    df_out = result.processed_route_analysis.route_data
    assert 0.0 in df_out[X_COL].values
    removed_x = {m.x_value for m in result.modification_log if m.modification_type == "point_removed"}
    assert 0.0 not in removed_x


@pytest.mark.unit
def test_linear_interpolate_skips_mandatory_breakpoint_with_nan():
    """NaN at a mandatory breakpoint is not interpolated by linear_interpolate."""
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [float("nan"), 1.0, 2.0, 3.0, 4.0]
    ra = _make_route_analysis(x, y)
    result = _run(ra, y_strategy="linear_interpolate")

    df_out = result.processed_route_analysis.route_data
    assert 0.0 in df_out[X_COL].values
    changed_x = {m.x_value for m in result.modification_log if m.modification_type in ("y_value_changed", "point_interpolated")}
    assert 0.0 not in changed_x


@pytest.mark.unit
def test_linear_interpolate_drops_when_no_right_neighbor():
    """NaN with no valid right neighbor (non-mandatory point) falls back to drop."""
    # x=3.0 has NaN; x=4.0 is mandatory but also NaN — no valid right neighbor.
    # x=3.0 is not mandatory so it can be dropped. x=4.0 (mandatory) is skipped.
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [0.0, 1.0, 2.0, float("nan"), float("nan")]
    ra = _make_route_analysis(x, y)
    result = _run(ra, y_strategy="linear_interpolate")

    removed = [m for m in result.modification_log if m.modification_type == "point_removed"]
    assert any(m.x_value == 3.0 for m in removed)
    assert not any(m.x_value == 4.0 for m in removed)


@pytest.mark.unit
def test_moving_average_uses_correct_window():
    """Window size limits how many neighbors are collected per side."""
    x = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    # NaN at x=3; neighbors: left=[2.0, 1.0, 0.0], right=[4.0, 5.0, 6.0]
    y = [0.0, 1.0, 2.0, float("nan"), 4.0, 5.0, 6.0]
    ra = _make_route_analysis(x, y)

    # window_size=1: only 1 neighbor per side → mean of [2.0, 4.0] = 3.0
    result = _run(ra, y_strategy="moving_average", window_size=1)
    df_out = result.processed_route_analysis.route_data
    row_3 = df_out.loc[df_out[X_COL] == 3.0, Y_COL].iloc[0]
    assert math.isclose(row_3, 3.0, rel_tol=1e-6)

    # window_size=3: 3 neighbors per side → mean of [0,1,2,4,5,6] = 18/6 = 3.0
    result2 = _run(ra, y_strategy="moving_average", window_size=3)
    df_out2 = result2.processed_route_analysis.route_data
    row_3b = df_out2.loc[df_out2[X_COL] == 3.0, Y_COL].iloc[0]
    assert math.isclose(row_3b, 3.0, rel_tol=1e-6)
