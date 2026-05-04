import sys
import os

import pytest


# Add src to path for imports
current_file_dir = os.path.dirname(__file__)  # tests/unit
tests_dir = os.path.dirname(current_file_dir)  # tests
project_root = os.path.dirname(tests_dir)  # highway_segmentation_tool
src_path = os.path.join(project_root, "src")

if src_path not in sys.path:
    sys.path.insert(0, src_path)

from config import NumericParameter


@pytest.mark.unit
def test_numeric_parameter_rejects_nan_values():
    p = NumericParameter(
        name="rate",
        display_name="Rate",
        description="test",
        group="g",
        order=1,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        decimal_places=3,
    )

    ok, _ = p.validate_value(float("nan"))
    assert ok is False

    ok, _ = p.validate_value("nan")
    assert ok is False

    ok, _ = p.validate_value(" NaN ")
    assert ok is False


@pytest.mark.unit
def test_numeric_parameter_rejects_nan_even_without_bounds():
    p = NumericParameter(
        name="x",
        display_name="X",
        description="test",
        group="g",
        order=1,
        default_value=1.0,
        decimal_places=2,
    )

    ok, msg = p.validate_value(float("nan"))
    assert ok is False
    assert "valid number" in msg.lower()
