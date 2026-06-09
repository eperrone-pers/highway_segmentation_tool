import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization.autoscale import autoscale_y_limits, visible_y_values_in_x_window


def test_autoscale_y_limits_none_for_empty_or_nonfinite():
    assert autoscale_y_limits([]) is None
    assert autoscale_y_limits([float("nan")]) is None
    assert autoscale_y_limits([float("inf"), float("-inf")]) is None


def test_autoscale_y_limits_applies_fractional_padding():
    y0, y1 = autoscale_y_limits([0.0, 10.0], pad_fraction=0.1, min_pad=1.0)
    assert y0 == -1.0
    assert y1 == 11.0


def test_autoscale_y_limits_uses_min_pad_when_flat():
    y0, y1 = autoscale_y_limits([5.0, 5.0], pad_fraction=0.1, min_pad=1.0)
    assert y0 == 4.0
    assert y1 == 6.0


def test_autoscale_y_limits_ignores_nan_in_mix():
    y0, y1 = autoscale_y_limits([float("nan"), 0.0, 10.0], pad_fraction=0.05, min_pad=1.0)
    # pad = 0.5
    assert y0 == -0.5
    assert y1 == 10.5


# ---------------------------------------------------------------------------
# visible_y_values_in_x_window
# ---------------------------------------------------------------------------

def test_visible_y_values_basic_filter():
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [10.0, 20.0, 30.0, 40.0, 50.0]
    result = visible_y_values_in_x_window(x, y, xmin=1.0, xmax=3.0)
    assert result is not None
    assert list(result) == [20.0, 30.0, 40.0]


def test_visible_y_values_overlay_scenario():
    # Simulates main data (x=0..4) extended with preprocessing overlay points
    # Original points outside the zoom window should not appear in result.
    main_x = [0.0, 1.0, 2.0, 3.0, 4.0]
    main_y = [10.0, 20.0, 30.0, 40.0, 50.0]
    overlay_x = [0.5, 3.5]   # one inside window [1,3], one outside
    overlay_y = [100.0, 200.0]

    all_x = main_x + overlay_x
    all_y = main_y + overlay_y

    result = visible_y_values_in_x_window(all_x, all_y, xmin=1.0, xmax=3.0)
    assert result is not None
    result_list = list(result)
    assert 20.0 in result_list   # main point at x=1
    assert 30.0 in result_list   # main point at x=2
    assert 40.0 in result_list   # main point at x=3
    assert 100.0 not in result_list  # overlay at x=0.5, outside window
    assert 200.0 not in result_list  # overlay at x=3.5, outside window


def test_visible_y_values_reversed_window():
    x = [0.0, 1.0, 2.0, 3.0]
    y = [10.0, 20.0, 30.0, 40.0]
    # xmin > xmax — normalize_xlim should handle it
    result = visible_y_values_in_x_window(x, y, xmin=3.0, xmax=1.0)
    assert result is not None
    assert set(result) == {20.0, 30.0, 40.0}


def test_visible_y_values_empty_result():
    x = [0.0, 1.0, 2.0]
    y = [10.0, 20.0, 30.0]
    result = visible_y_values_in_x_window(x, y, xmin=5.0, xmax=10.0)
    assert result is None


def test_visible_y_values_length_mismatch_returns_none():
    # Documents the guard: mismatched arrays return None rather than raising.
    x = [0.0, 1.0, 2.0]
    y = [10.0, 20.0]
    result = visible_y_values_in_x_window(x, y, xmin=0.0, xmax=2.0)
    assert result is None
