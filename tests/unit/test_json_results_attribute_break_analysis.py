from analysis.base import AnalysisResult

from json_results_manager import JsonResultsManager


def test_json_results_manager_emits_attribute_break_analysis():
    mgr = JsonResultsManager()

    res = AnalysisResult(
        method_name="m",
        method_key="single",
        route_id="R",
        all_solutions=[{"chromosome": [0.0, 1.0]}],
        mandatory_breakpoints=[0.0, 1.0],
        data_summary={
            "total_data_points": 3,
            "data_range": {"x_min": 0.0, "x_max": 1.0, "y_min": 0.0, "y_max": 1.0},
            "gap_analysis": {"total_gaps": 0, "gap_segments": [], "total_gap_length": 0.0},
            "attribute_break_analysis": {
                "columns_used": ["district"],
                "break_events": [{"x": 0.5, "changed_columns": ["district"], "signature": "district"}],
                "breakpoints": [0.5],
                "total_attribute_breaks": 1,
            },
        },
    )

    block = mgr._build_input_data_analysis(res)
    assert "attribute_break_analysis" in block
    assert block["attribute_break_analysis"]["columns_used"] == ["district"]
