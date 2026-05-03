import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization.results_binding import resolve_xy_columns


def test_resolve_xy_columns_prefers_route_processing():
    json_results = {
        "input_parameters": {"route_processing": {"x_column": "mp", "y_column": "iri"}},
        "analysis_metadata": {
            "input_file_info": {
                "column_info": {"x_column": "fallback_x", "y_column": "fallback_y"}
            }
        },
    }

    res = resolve_xy_columns(json_results)
    assert res.x_col == "mp"
    assert res.y_col == "iri"
    assert res.error_message is None


def test_resolve_xy_columns_uses_column_info_backup():
    json_results = {
        "input_parameters": {"route_processing": {}},
        "analysis_metadata": {
            "input_file_info": {"column_info": {"x_column": "x2", "y_column": "y2"}}
        },
    }

    res = resolve_xy_columns(json_results)
    assert res.x_col == "x2"
    assert res.y_col == "y2"
    assert res.error_message is None


def test_resolve_xy_columns_strict_missing_returns_error():
    json_results = {"input_parameters": {"route_processing": {"x_column": "x_only"}}}

    res = resolve_xy_columns(json_results)
    assert res.x_col == "x_only"
    assert res.y_col is None
    assert res.error_message
