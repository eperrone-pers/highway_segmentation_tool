import sys
from pathlib import Path

import numpy as np

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization.autoscale import visible_y_values_in_x_window


def test_visible_y_values_in_x_window_selects_inclusive_range():
    x = np.array([0.0, 5.0, 10.0])
    y = np.array([1.0, 2.0, 3.0])

    out = visible_y_values_in_x_window(x, y, xmin=0.0, xmax=5.0)
    assert out.tolist() == [1.0, 2.0]


def test_visible_y_values_in_x_window_handles_reversed_window():
    x = np.array([0.0, 5.0, 10.0])
    y = np.array([1.0, 2.0, 3.0])

    out = visible_y_values_in_x_window(x, y, xmin=6.0, xmax=4.0)
    assert out.tolist() == [2.0]


def test_visible_y_values_in_x_window_returns_none_when_no_points():
    x = np.array([0.0, 5.0, 10.0])
    y = np.array([1.0, 2.0, 3.0])

    assert visible_y_values_in_x_window(x, y, xmin=11.0, xmax=12.0) is None


def test_visible_y_values_in_x_window_returns_none_for_mismatched_lengths():
    assert visible_y_values_in_x_window([0.0, 1.0], [1.0], xmin=0.0, xmax=1.0) is None
