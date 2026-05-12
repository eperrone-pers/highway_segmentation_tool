import sys
from pathlib import Path

import pandas as pd

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization.break_lanes import attribute_breakpoints_by_column, compute_lane_boxes


def test_attribute_breakpoints_by_column_groups_breaks_per_changed_column():
    attr_block = {
        "break_events": [
            {"x": 10, "changed_columns": ["A"]},
            {"x": 20, "changed_columns": ["A", "B"]},
            {"x": "30", "changed_columns": ["B"]},
        ]
    }

    out = attribute_breakpoints_by_column(attr_block)
    assert out["A"] == [10.0, 20.0]
    assert out["B"] == [20.0, 30.0]


def test_compute_lane_boxes_uses_nearest_midpoint_value():
    df = pd.DataFrame(
        {
            "x": [0, 5, 10, 15, 20],
            "A": ["a0", "a0", "a1", "a1", "a2"],
        }
    )

    boxes = compute_lane_boxes(
        x_values=df["x"].tolist(),
        attribute_values=df["A"].tolist(),
        lane_breakpoints=[10, 20],
        x_min=0,
        x_max=20,
    )

    assert [(b.start_x, b.end_x) for b in boxes] == [(0.0, 10.0), (10.0, 20.0)]
    # Midpoints are 5 and 15 -> nearest values are a0 and a1
    assert [b.value for b in boxes] == ["a0", "a1"]
