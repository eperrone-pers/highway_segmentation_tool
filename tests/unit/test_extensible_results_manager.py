from unittest.mock import Mock

import pandas as pd

from analysis.base import AnalysisResult
from extensible_results_manager import ExtensibleJsonResultsManager


def test_extensible_manager_reuses_base_processing_results_and_adds_segment_details():
    mgr = ExtensibleJsonResultsManager()
    result = AnalysisResult(
        method_name="Single",
        method_key="single",
        route_id="R1",
        all_solutions=[{"chromosome": [0.0, 1.0], "fitness": 1.23}],
        mandatory_breakpoints=[0.0, 1.0],
        data_summary={"gap_analysis": {"gap_segments": []}},
    )

    base_processing_results = {
        "pareto_points": [{
            "point_id": 0,
            "objective_values": [1.23],
            "segmentation": {
                "breakpoints": [0.0, 1.0],
                "segment_count": 1,
                "segment_lengths": [1.0],
                "total_length": 1.0,
                "average_segment_length": 1.0,
            },
        }]
    }
    mgr.base_json_manager._build_processing_results = Mock(return_value=base_processing_results)

    processing_results = mgr._build_processing_results(
        result,
        original_data_by_route={
            "R1": pd.DataFrame({"X": [0.0, 1.0], "Y": [10.0, 20.0]})
        },
        route_processing_info={"x_column": "X", "y_column": "Y"},
    )

    mgr.base_json_manager._build_processing_results.assert_called_once_with(result)
    pareto_point = processing_results["pareto_points"][0]

    assert pareto_point["objective_values"] == [1.23]
    assert pareto_point["segmentation"]["segment_count"] == 1
    assert pareto_point["segmentation"]["segment_details"] == [{
        "segment_index": 0,
        "start": 0.0,
        "end": 1.0,
        "length": 1.0,
        "is_mandatory": True,
        "data_point_count": 2,
        "y_value_min": 10.0,
        "y_value_max": 20.0,
        "y_value_avg": 15.0,
        "y_value_std": 5.0,
    }]