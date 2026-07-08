"""Integration tests for lane/direction column and x-range filter support.

These tests run the full CLI pipeline (load → composite key build → analysis →
JSON output) against TestLaneDirection.csv, which contains:

  Group                   | Rows | Composite key
  ----------------------- | ---- | -------------------------
  TestRoute1 / NB  / K1   |  20  | TestRoute1|NB|K1
  TestRoute1 / NB  / K6   |  20  | TestRoute1|NB|K6
  TestRoute1 / SB  / K1   |  20  | TestRoute1|SB|K1
  TestRoute2 / NB  / K1   |  20  | TestRoute2|NB|K1
  TestRoute2 / null/ K1   |  10  | TestRoute2|NULL|K1
  TestRoute2 / NB  / null |  10  | TestRoute2|NB|NULL
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from cli_runner import RunSpecError, run_analysis_from_spec_file
from csv_export import segments_to_dataframe

_TEST_DATA = _REPO_ROOT / "tests" / "test_data" / "TestLaneDirection.csv"
_NOLOG = lambda _: None  # noqa: E731


def _write_spec(tmp_path: Path, **input_overrides) -> Path:
    """Write a run spec using TestLaneDirection.csv and return its path."""
    spec = {
        "spec_version": "1.0.0",
        "input": {
            "data_file_path": str(_TEST_DATA),
            "x_column": "BDFO",
            "y_column": "SCI",
            "gap_threshold": 0.5,
            "route_column": "RDB",
            **input_overrides,
        },
        "method": {"method_key": "aashto_cda", "method_parameters": {}},
        "output": {
            "output_json_path": str(tmp_path / "results.json"),
            "overwrite": True,
        },
    }
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return p


def _run(spec_path: Path) -> dict:
    out = run_analysis_from_spec_file(spec_path, validate_spec=True, log_callback=_NOLOG)
    return json.loads(Path(out).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Core composite key tests
# ---------------------------------------------------------------------------

@pytest.mark.file_io
def test_all_three_columns_produce_six_route_groups(tmp_path: Path) -> None:
    """With route + direction + lane all set, exactly 6 composite groups are produced."""
    data = _run(_write_spec(tmp_path, direction_column="DIRECTION", lane_column="LANE"))

    route_ids = [r["route_info"]["route_id"] for r in data["route_results"]]
    assert len(route_ids) == 6

    expected = {
        "TestRoute1|NB|K1",
        "TestRoute1|NB|K6",
        "TestRoute1|SB|K1",
        "TestRoute2|NB|K1",
        "TestRoute2|NULL|K1",
        "TestRoute2|NB|NULL",
    }
    assert set(route_ids) == expected


@pytest.mark.file_io
def test_route_and_direction_only_produces_four_groups(tmp_path: Path) -> None:
    """With route + direction (no lane), K1 and K6 merge → 4 groups."""
    data = _run(_write_spec(tmp_path, direction_column="DIRECTION"))

    route_ids = {r["route_info"]["route_id"] for r in data["route_results"]}
    # K1 and K6 rows for same route+direction merge into one group
    assert len(route_ids) == 4
    assert "TestRoute1|NB" in route_ids
    assert "TestRoute1|SB" in route_ids
    assert "TestRoute2|NB" in route_ids
    assert "TestRoute2|NULL" in route_ids


@pytest.mark.file_io
def test_route_and_lane_only_produces_four_groups(tmp_path: Path) -> None:
    """With route + lane (no direction), NB/SB rows merge → 4 groups."""
    data = _run(_write_spec(tmp_path, lane_column="LANE"))

    route_ids = {r["route_info"]["route_id"] for r in data["route_results"]}
    assert len(route_ids) == 4
    assert "TestRoute1|K1" in route_ids
    assert "TestRoute1|K6" in route_ids
    assert "TestRoute2|K1" in route_ids
    assert "TestRoute2|NULL" in route_ids


@pytest.mark.file_io
def test_no_lane_direction_columns_produces_two_groups(tmp_path: Path) -> None:
    """Baseline: without lane/direction the existing route column gives 2 groups."""
    data = _run(_write_spec(tmp_path))

    route_ids = {r["route_info"]["route_id"] for r in data["route_results"]}
    assert route_ids == {"TestRoute1", "TestRoute2"}


# ---------------------------------------------------------------------------
# Null handling in composite keys
# ---------------------------------------------------------------------------

@pytest.mark.file_io
def test_null_direction_rows_form_own_group(tmp_path: Path) -> None:
    """Rows with null direction are grouped as 'TestRoute2|NULL|K1', not dropped."""
    data = _run(_write_spec(tmp_path, direction_column="DIRECTION", lane_column="LANE"))
    route_ids = {r["route_info"]["route_id"] for r in data["route_results"]}
    assert "TestRoute2|NULL|K1" in route_ids


@pytest.mark.file_io
def test_null_lane_rows_form_own_group(tmp_path: Path) -> None:
    """Rows with null lane are grouped as 'TestRoute2|NB|NULL', not dropped."""
    data = _run(_write_spec(tmp_path, direction_column="DIRECTION", lane_column="LANE"))
    route_ids = {r["route_info"]["route_id"] for r in data["route_results"]}
    assert "TestRoute2|NB|NULL" in route_ids


# ---------------------------------------------------------------------------
# x-range filter
# ---------------------------------------------------------------------------

@pytest.mark.file_io
def test_x_min_excludes_rows_below_threshold(tmp_path: Path) -> None:
    """x_min=0.05 cuts 5 rows from each TestRoute1 group (BDFO 0.00–0.04).

    TestRoute1 groups start at BDFO 0.0 so x_min=0.05 reduces their row count.
    TestRoute2 groups start at BDFO ~196.8 and are unaffected.
    """
    data_full = _run(_write_spec(tmp_path, direction_column="DIRECTION", lane_column="LANE"))
    tmp2 = tmp_path / "filtered"
    tmp2.mkdir()
    data_filtered = _run(_write_spec(tmp2, direction_column="DIRECTION", lane_column="LANE", x_min=0.05))

    full_counts = {
        r["route_info"]["route_id"]: r["input_data_analysis"]["data_summary"]["total_data_points"]
        for r in data_full["route_results"]
    }
    filtered_counts = {
        r["route_info"]["route_id"]: r["input_data_analysis"]["data_summary"]["total_data_points"]
        for r in data_filtered["route_results"]
    }
    # TestRoute1 groups (BDFO starts at 0.0) must have fewer points after filter
    affected = ["TestRoute1|NB|K1", "TestRoute1|NB|K6", "TestRoute1|SB|K1"]
    for route_id in affected:
        assert filtered_counts[route_id] < full_counts[route_id], (
            f"Route {route_id}: expected fewer points after x_min=0.05 filter"
        )
    # Total row count across all groups must be lower
    assert sum(filtered_counts.values()) < sum(full_counts.values())


@pytest.mark.file_io
def test_x_max_excludes_rows_above_threshold(tmp_path: Path) -> None:
    """x_max=0.05 keeps only the first 5 rows of every group."""
    data = _run(_write_spec(tmp_path, direction_column="DIRECTION", lane_column="LANE", x_max=0.05))

    for r in data["route_results"]:
        pts = r["input_data_analysis"]["data_summary"]["total_data_points"]
        assert pts <= 6, (
            f"Route {r['route_info']['route_id']} has {pts} points after x_max=0.05 filter, expected ≤ 6"
        )


@pytest.mark.file_io
def test_x_min_greater_than_x_max_produces_no_routes(tmp_path: Path) -> None:
    """x_min > x_max leaves zero rows → RunSpecError about no routes."""
    with pytest.raises(Exception):
        _run(_write_spec(tmp_path, x_min=10.0, x_max=0.0))


# ---------------------------------------------------------------------------
# selected_routes with composite keys
# ---------------------------------------------------------------------------

@pytest.mark.file_io
def test_selected_routes_filters_to_composite_keys(tmp_path: Path) -> None:
    """selected_routes containing composite key strings selects only those groups."""
    data = _run(_write_spec(
        tmp_path,
        direction_column="DIRECTION",
        lane_column="LANE",
        selected_routes=["TestRoute1|NB|K1", "TestRoute2|NB|K1"],
    ))

    route_ids = {r["route_info"]["route_id"] for r in data["route_results"]}
    assert route_ids == {"TestRoute1|NB|K1", "TestRoute2|NB|K1"}


# ---------------------------------------------------------------------------
# Metadata in JSON output
# ---------------------------------------------------------------------------

@pytest.mark.file_io
def test_direction_and_lane_column_names_in_output_metadata(tmp_path: Path) -> None:
    """direction_column and lane_column are recorded in route_processing_info."""
    data = _run(_write_spec(tmp_path, direction_column="DIRECTION", lane_column="LANE"))

    rp = data["input_parameters"]["route_processing"]
    assert rp.get("direction_column") == "DIRECTION"
    assert rp.get("lane_column") == "LANE"


@pytest.mark.file_io
def test_composite_route_components_in_output_metadata(tmp_path: Path) -> None:
    """composite_route_components records the active join order."""
    data = _run(_write_spec(tmp_path, direction_column="DIRECTION", lane_column="LANE"))

    rp = data["input_parameters"]["route_processing"]
    components = rp.get("composite_route_components")
    assert components == ["RDB", "DIRECTION", "LANE"]


@pytest.mark.file_io
def test_x_min_x_max_in_output_metadata(tmp_path: Path) -> None:
    """x_min and x_max are recorded in route_processing_info."""
    data = _run(_write_spec(tmp_path, x_min=0.02, x_max=0.15))

    rp = data["input_parameters"]["route_processing"]
    assert rp.get("x_min") == pytest.approx(0.02)
    assert rp.get("x_max") == pytest.approx(0.15)


@pytest.mark.file_io
def test_route_column_none_direction_and_lane_only(tmp_path: Path) -> None:
    """When route_column is omitted, direction+lane alone form the composite keys."""
    spec_path = _write_spec(tmp_path, direction_column="DIRECTION", lane_column="LANE")
    # Overwrite with route_column absent
    spec = json.loads(spec_path.read_text())
    del spec["input"]["route_column"]  # omit entirely
    spec_path.write_text(json.dumps(spec, indent=2))

    data = _run(spec_path)
    route_ids = {r["route_info"]["route_id"] for r in data["route_results"]}

    # Without route_column, NB+K1 rows from TestRoute1 and TestRoute2 merge
    # Expected groups: NB|K1, NB|K6, SB|K1, NULL|K1, NB|NULL
    assert len(route_ids) == 5
    assert "NB|K1" in route_ids
    assert "NB|K6" in route_ids
    assert "SB|K1" in route_ids
    assert "NULL|K1" in route_ids
    assert "NB|NULL" in route_ids


@pytest.mark.file_io
def test_route_column_none_direction_only(tmp_path: Path) -> None:
    """With route_column absent and only direction_column set, data groups by direction."""
    spec_path = _write_spec(tmp_path, direction_column="DIRECTION")
    spec = json.loads(spec_path.read_text())
    del spec["input"]["route_column"]
    spec_path.write_text(json.dumps(spec, indent=2))

    data = _run(spec_path)
    route_ids = {r["route_info"]["route_id"] for r in data["route_results"]}

    # All K1/K6 rows with same direction merge → NB, SB, NULL
    assert route_ids == {"NB", "SB", "NULL"}


@pytest.mark.file_io
def test_all_grouping_columns_none_is_single_route_mode(tmp_path: Path) -> None:
    """With route_column, direction_column, and lane_column all absent, entire dataset
    is treated as a single route."""
    spec = {
        "spec_version": "1.0.0",
        "input": {
            "data_file_path": str(_TEST_DATA),
            "x_column": "BDFO",
            "y_column": "SCI",
            "gap_threshold": 0.5,
            # no route_column, no direction_column, no lane_column
        },
        "method": {"method_key": "aashto_cda", "method_parameters": {}},
        "output": {"output_json_path": str(tmp_path / "results.json"), "overwrite": True},
    }
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec, indent=2))

    data = _run(p)
    # Single-route mode → exactly one result entry
    assert len(data["route_results"]) == 1


@pytest.mark.file_io
def test_x_range_drops_route_with_no_matching_data_logs_message(tmp_path: Path) -> None:
    """When x_max cuts off an entire route group, that group is skipped with a log message.

    TestRoute1 groups have BDFO 0.0–0.187; TestRoute2 groups have BDFO ~196–197.
    Setting x_max=0.2 eliminates all TestRoute2 groups while keeping TestRoute1 groups.
    """
    log_messages: list[str] = []
    spec_path = _write_spec(
        tmp_path,
        direction_column="DIRECTION",
        lane_column="LANE",
        x_max=0.2,
    )
    out = run_analysis_from_spec_file(
        spec_path, validate_spec=True, log_callback=log_messages.append
    )
    data = json.loads(Path(out).read_text(encoding="utf-8"))

    # Only TestRoute1 groups should remain in results
    route_ids = {r["route_info"]["route_id"] for r in data["route_results"]}
    assert all(rid.startswith("TestRoute1") for rid in route_ids)
    assert len(route_ids) == 3  # NB|K1, NB|K6, SB|K1

    # Log should mention the dropped TestRoute2 groups
    skip_msgs = [m for m in log_messages if "skipped" in m.lower() and "x-range" in m.lower()]
    assert len(skip_msgs) == 3, (
        f"Expected 3 skip messages for TestRoute2 groups, got {len(skip_msgs)}:\n"
        + "\n".join(skip_msgs)
    )
    assert any("TestRoute2" in m for m in skip_msgs)


@pytest.mark.file_io
def test_x_range_route_with_partial_data_not_skipped(tmp_path: Path) -> None:
    """A route with SOME rows in the x-range is analyzed normally, not skipped."""
    log_messages: list[str] = []
    # x_min=0.05 cuts a few rows from TestRoute1 groups but doesn't remove them entirely
    spec_path = _write_spec(
        tmp_path,
        direction_column="DIRECTION",
        lane_column="LANE",
        x_min=0.05,
    )
    out = run_analysis_from_spec_file(
        spec_path, validate_spec=True, log_callback=log_messages.append
    )
    data = json.loads(Path(out).read_text(encoding="utf-8"))

    # All 6 groups should still be present (none completely eliminated)
    route_ids = {r["route_info"]["route_id"] for r in data["route_results"]}
    assert len(route_ids) == 6

    # No skip messages should appear
    skip_msgs = [m for m in log_messages if "skipped" in m.lower() and "x-range" in m.lower()]
    assert skip_msgs == []


@pytest.mark.file_io
def test_absent_direction_lane_not_in_metadata(tmp_path: Path) -> None:
    """When not configured, direction_column/lane_column are absent from metadata."""
    data = _run(_write_spec(tmp_path))

    rp = data["input_parameters"]["route_processing"]
    assert "direction_column" not in rp
    assert "lane_column" not in rp
    assert "composite_route_components" not in rp


# ---------------------------------------------------------------------------
# Step 6: Output format — route_info decomposition
# ---------------------------------------------------------------------------

@pytest.mark.file_io
def test_route_info_contains_decomposed_fields_for_composite_key(tmp_path: Path) -> None:
    """With all 3 columns active, each route_info gets route/direction/lane fields."""
    data = _run(_write_spec(tmp_path, direction_column="DIRECTION", lane_column="LANE"))

    for r in data["route_results"]:
        ri = r["route_info"]
        assert "route_id" in ri
        assert "route" in ri, f"Missing 'route' in {ri}"
        assert "direction" in ri, f"Missing 'direction' in {ri}"
        assert "lane" in ri, f"Missing 'lane' in {ri}"

    # Spot-check decomposition of one known route
    by_id = {r["route_info"]["route_id"]: r["route_info"] for r in data["route_results"]}
    ri = by_id["TestRoute1|NB|K1"]
    assert ri["route"] == "TestRoute1"
    assert ri["direction"] == "NB"
    assert ri["lane"] == "K1"


@pytest.mark.file_io
def test_route_info_null_component_preserved_as_NULL_literal(tmp_path: Path) -> None:
    """Null direction rows have direction='NULL' in their route_info."""
    data = _run(_write_spec(tmp_path, direction_column="DIRECTION", lane_column="LANE"))
    by_id = {r["route_info"]["route_id"]: r["route_info"] for r in data["route_results"]}

    ri = by_id["TestRoute2|NULL|K1"]
    assert ri["direction"] == "NULL"
    assert ri["lane"] == "K1"


@pytest.mark.file_io
def test_route_info_no_extra_fields_when_no_composite(tmp_path: Path) -> None:
    """Without direction/lane, route_info only contains route_id (baseline)."""
    data = _run(_write_spec(tmp_path))

    for r in data["route_results"]:
        ri = r["route_info"]
        assert set(ri.keys()) == {"route_id"}, f"Unexpected keys in route_info: {ri}"


@pytest.mark.file_io
def test_route_info_direction_only_composite(tmp_path: Path) -> None:
    """With route + direction only, route_info has route and direction but no lane."""
    data = _run(_write_spec(tmp_path, direction_column="DIRECTION"))

    for r in data["route_results"]:
        ri = r["route_info"]
        assert "route" in ri
        assert "direction" in ri
        assert "lane" not in ri


# ---------------------------------------------------------------------------
# Step 6: CSV export — component columns
# ---------------------------------------------------------------------------

@pytest.mark.file_io
def test_csv_export_includes_component_columns(tmp_path: Path) -> None:
    """segments_to_dataframe adds route/direction/lane columns after route_id."""
    data = _run(_write_spec(tmp_path, direction_column="DIRECTION", lane_column="LANE"))

    df = segments_to_dataframe(data)
    assert not df.empty
    assert "route_id" in df.columns
    assert "route" in df.columns
    assert "direction" in df.columns
    assert "lane" in df.columns

    # Column order: route_id, route, direction, lane, then segment data
    cols = list(df.columns)
    assert cols.index("route_id") < cols.index("route")
    assert cols.index("route") < cols.index("direction")
    assert cols.index("direction") < cols.index("lane")
    assert cols.index("lane") < cols.index("segment_index")


@pytest.mark.file_io
def test_csv_export_no_extra_columns_without_composite(tmp_path: Path) -> None:
    """Without direction/lane, CSV has no extra component columns."""
    data = _run(_write_spec(tmp_path))

    df = segments_to_dataframe(data)
    assert "route" not in df.columns
    assert "direction" not in df.columns
    assert "lane" not in df.columns


@pytest.mark.file_io
def test_csv_export_values_match_route_info(tmp_path: Path) -> None:
    """Component column values in CSV match the route_info decomposition."""
    data = _run(_write_spec(tmp_path, direction_column="DIRECTION", lane_column="LANE"))

    df = segments_to_dataframe(data)
    route1_nb_k1 = df[df["route_id"] == "TestRoute1|NB|K1"]
    assert not route1_nb_k1.empty
    assert (route1_nb_k1["route"] == "TestRoute1").all()
    assert (route1_nb_k1["direction"] == "NB").all()
    assert (route1_nb_k1["lane"] == "K1").all()
