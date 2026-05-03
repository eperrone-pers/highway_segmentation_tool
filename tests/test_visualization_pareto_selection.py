import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization.pareto import choose_selected_pareto_point


def test_choose_selected_pareto_point_matches_id():
    points = [
        {"point_id": 1, "segmentation": {}},
        {"point_id": 2, "segmentation": {"breakpoints": [1, 2]}},
    ]

    selected = choose_selected_pareto_point(points, 2)
    assert selected is points[1]


def test_choose_selected_pareto_point_falls_back_to_first_when_not_found():
    points = [{"point_id": 1}, {"point_id": 2}]

    selected = choose_selected_pareto_point(points, 999)
    assert selected is points[0]


def test_choose_selected_pareto_point_returns_none_when_empty():
    assert choose_selected_pareto_point([], 1) is None
