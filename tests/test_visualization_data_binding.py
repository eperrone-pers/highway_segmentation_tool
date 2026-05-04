import sys
from pathlib import Path

import pandas as pd

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization.results_binding import (
    routes_from_json_results,
    routes_from_original_data,
    resolve_routes,
    group_original_data_by_route,
)


def test_routes_from_json_results_extracts_route_ids():
    json_results = {
        "route_results": [
            {"route_info": {"route_id": 268296608}},
            {"route_info": {"route_id": " R2 "}},
        ]
    }
    assert routes_from_json_results(json_results) == ["268296608", "R2"]


def test_routes_from_original_data_uses_column_and_normalizes():
    df = pd.DataFrame({"ROUTE": [" A ", None, "null", "B"]})
    assert routes_from_original_data(df, "ROUTE") == ["A", "null", "B"]


def test_resolve_routes_prefers_json_over_original():
    df = pd.DataFrame({"ROUTE": ["A", "B"]})
    json_results = {"route_results": [{"route_info": {"route_id": "R1"}}]}
    assert resolve_routes(json_results, df, "ROUTE") == ["R1"]


def test_group_original_data_by_route_groups_rows():
    df = pd.DataFrame({"ROUTE": ["A", "A", "B"], "x": [1, 2, 3]})
    grouped = group_original_data_by_route(df, ["A", "B"], "ROUTE")
    assert set(grouped.keys()) == {"A", "B"}
    assert len(grouped["A"]) == 2
    assert len(grouped["B"]) == 1


def test_group_original_data_by_route_falls_back_to_single_route_when_missing_column():
    df = pd.DataFrame({"x": [1, 2, 3]})
    grouped = group_original_data_by_route(df, ["Route1"], None)
    assert list(grouped.keys()) == ["Route1"]
    assert len(grouped["Route1"]) == 3
