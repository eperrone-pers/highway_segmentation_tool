import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization.autoscale import autoscale_y_limits


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
