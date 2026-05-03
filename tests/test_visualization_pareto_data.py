import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization.pareto import prepare_pareto_series


def test_prepare_pareto_series_applies_negate_transform_for_multi_method():
    # Method 'multi' is configured with objective_plot_configs where the first objective
    # uses transform='negate' (see config.py).
    json_results = {"analysis_metadata": {"analysis_method": "multi"}}
    pareto_points = [
        {"objective_values": [-10.0, 2.5], "point_id": 1},
        {"objective_values": [-5.0, 3.0], "point_id": 2},
    ]

    series = prepare_pareto_series(json_results, pareto_points)

    assert series.x_values == [10.0, 5.0]
    assert series.y_values == [2.5, 3.0]
    assert series.point_ids == [1, 2]
    assert series.x_label
    assert series.y_label


def test_prepare_pareto_series_empty_when_objectives_missing():
    json_results = {"analysis_metadata": {"analysis_method": "multi"}}
    pareto_points = [{"objective_values": [1.0], "point_id": 1}]

    series = prepare_pareto_series(json_results, pareto_points)
    assert series.x_values == []
    assert series.y_values == []
