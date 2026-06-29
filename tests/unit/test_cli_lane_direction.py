"""Unit tests for lane/direction/x-range additions to cli_runner and run_spec."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cli_runner import (
    ResolvedRunSpec,
    RunSpecError,
    _convert_columns_for_analysis,
    load_and_resolve_run_spec,
)
from run_spec import build_run_spec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_SPEC_BASE = {
    "spec_version": "1.0.0",
    "input": {
        "data_file_path": "data/test.csv",
        "x_column": "BDFO",
        "y_column": "SCI",
        "gap_threshold": 0.1,
    },
    "method": {"method_key": "aashto_cda", "method_parameters": {}},
    "output": {"output_json_path": "out/results.json"},
}


def _spec_with(**input_overrides) -> dict:
    """Return a minimal spec dict with extra input fields merged in."""
    spec = json.loads(json.dumps(_MINIMAL_SPEC_BASE))
    spec["input"].update(input_overrides)
    return spec


def _load_spec_from_dict(tmp_path: Path, spec_dict: dict) -> ResolvedRunSpec:
    """Write spec_dict to a temp file and load it via load_and_resolve_run_spec."""
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec_dict))
    return load_and_resolve_run_spec(p, validate=False)


# ---------------------------------------------------------------------------
# Schema validation — new fields accepted
# ---------------------------------------------------------------------------

def test_schema_accepts_direction_and_lane_columns() -> None:
    import jsonschema
    schema_path = Path(__file__).resolve().parents[2] / "src" / "highway_segmentation_run_spec_schema.json"
    schema = json.loads(schema_path.read_text())
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())

    instance = _spec_with(direction_column="DIRECTION", lane_column="LANE")
    errors = list(validator.iter_errors(instance))
    assert errors == [], [f"{e.json_path}: {e.message}" for e in errors]


def test_schema_accepts_x_min_and_x_max() -> None:
    import jsonschema
    schema_path = Path(__file__).resolve().parents[2] / "src" / "highway_segmentation_run_spec_schema.json"
    schema = json.loads(schema_path.read_text())
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())

    instance = _spec_with(x_min=1.5, x_max=8.0)
    errors = list(validator.iter_errors(instance))
    assert errors == [], [f"{e.json_path}: {e.message}" for e in errors]


def test_schema_accepts_null_new_fields() -> None:
    import jsonschema
    schema_path = Path(__file__).resolve().parents[2] / "src" / "highway_segmentation_run_spec_schema.json"
    schema = json.loads(schema_path.read_text())
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())

    instance = _spec_with(direction_column=None, lane_column=None, x_min=None, x_max=None)
    errors = list(validator.iter_errors(instance))
    assert errors == [], [f"{e.json_path}: {e.message}" for e in errors]


# ---------------------------------------------------------------------------
# Spec parsing — new fields round-trip through load_and_resolve_run_spec
# ---------------------------------------------------------------------------

def test_parse_direction_and_lane_columns(tmp_path: Path) -> None:
    spec = load_and_resolve_run_spec(
        _load_spec_from_dict(tmp_path, _spec_with(direction_column="DIR", lane_column="LANE")).spec_path,
        validate=False,
    )
    # Re-load to verify persistence through the file round-trip
    resolved = _load_spec_from_dict(tmp_path, _spec_with(direction_column="DIR", lane_column="LANE"))
    assert resolved.direction_column == "DIR"
    assert resolved.lane_column == "LANE"


def test_parse_x_min_and_x_max(tmp_path: Path) -> None:
    resolved = _load_spec_from_dict(tmp_path, _spec_with(x_min=2.0, x_max=9.5))
    assert resolved.x_min == pytest.approx(2.0)
    assert resolved.x_max == pytest.approx(9.5)


def test_parse_null_fields_become_none(tmp_path: Path) -> None:
    resolved = _load_spec_from_dict(
        tmp_path,
        _spec_with(direction_column=None, lane_column=None, x_min=None, x_max=None),
    )
    assert resolved.direction_column is None
    assert resolved.lane_column is None
    assert resolved.x_min is None
    assert resolved.x_max is None


def test_parse_absent_fields_become_none(tmp_path: Path) -> None:
    """Fields not present in spec at all should default to None."""
    resolved = _load_spec_from_dict(tmp_path, _MINIMAL_SPEC_BASE)
    assert resolved.direction_column is None
    assert resolved.lane_column is None
    assert resolved.x_min is None
    assert resolved.x_max is None


# ---------------------------------------------------------------------------
# build_run_spec — new fields emitted
# ---------------------------------------------------------------------------

def test_build_run_spec_includes_new_fields() -> None:
    spec = build_run_spec(
        data_file_path="data/test.csv",
        x_column="BDFO",
        y_column="SCI",
        gap_threshold=0.1,
        method_key="aashto_cda",
        method_parameters={},
        output_json_path="out/results.json",
        direction_column="DIRECTION",
        lane_column="LANE",
        x_min=1.0,
        x_max=10.0,
    )
    assert spec["input"]["direction_column"] == "DIRECTION"
    assert spec["input"]["lane_column"] == "LANE"
    assert spec["input"]["x_min"] == 1.0
    assert spec["input"]["x_max"] == 10.0


def test_build_run_spec_new_fields_default_to_none() -> None:
    spec = build_run_spec(
        data_file_path="data/test.csv",
        x_column="BDFO",
        y_column="SCI",
        gap_threshold=0.1,
        method_key="aashto_cda",
        method_parameters={},
        output_json_path="out/results.json",
    )
    assert spec["input"]["direction_column"] is None
    assert spec["input"]["lane_column"] is None
    assert spec["input"]["x_min"] is None
    assert spec["input"]["x_max"] is None


# ---------------------------------------------------------------------------
# _convert_columns_for_analysis — direction/lane kept as strings
# ---------------------------------------------------------------------------

def test_direction_and_lane_not_coerced_to_numeric() -> None:
    """direction/lane columns that look numeric (e.g. "1", "2") must stay as strings."""
    df = pd.DataFrame({
        "BDFO": ["0.0", "0.01", "0.02"],
        "SCI": ["2.2", "0.9", "1.1"],
        "RDB": ["R1", "R1", "R1"],
        "DIR": ["NB", "NB", "SB"],
        "LANE": ["1", "2", "1"],  # numeric-looking but must stay as string
    })
    result = _convert_columns_for_analysis(
        df,
        x_column="BDFO",
        y_column="SCI",
        route_column="RDB",
        direction_column="DIR",
        lane_column="LANE",
    )
    assert result["DIR"].dtype == object or str(result["DIR"].dtype) == "string"
    assert result["LANE"].dtype == object or str(result["LANE"].dtype) == "string"
    # Values must not have become floats
    assert "1.0" not in result["LANE"].values
    assert "1" in result["LANE"].values or 1 not in result["LANE"].values


def test_direction_lane_stripped_of_whitespace() -> None:
    df = pd.DataFrame({
        "BDFO": ["0.0", "0.01"],
        "SCI": ["2.2", "0.9"],
        "RDB": ["R1", "R1"],
        "DIR": [" NB ", " SB"],
        "LANE": ["K1 ", " K6"],
    })
    result = _convert_columns_for_analysis(
        df, x_column="BDFO", y_column="SCI",
        route_column="RDB", direction_column="DIR", lane_column="LANE",
    )
    assert list(result["DIR"]) == ["NB", "SB"]
    assert list(result["LANE"]) == ["K1", "K6"]


# ---------------------------------------------------------------------------
# x_min / x_max row-filtering behaviour
# ---------------------------------------------------------------------------

_TEST_CSV = str(Path(__file__).resolve().parents[2] / "tests" / "test_data" / "TestLaneDirection.csv")
# BDFO=0.05 appears in the test CSV; used to verify boundary-inclusive semantics.
_BOUNDARY_X = 0.05


def _run_spec_file(tmp_path: Path, **input_overrides) -> dict:
    """Build and run a minimal aashto_cda spec against TestLaneDirection.csv."""
    from cli_runner import run_analysis_from_spec_file

    out_path = tmp_path / "out.json"
    spec = {
        "spec_version": "1.0.0",
        "input": {
            "data_file_path": _TEST_CSV,
            "x_column": "BDFO",
            "y_column": "SCI",
            "route_column": "RDB",
            "gap_threshold": 50.0,
            **input_overrides,
        },
        "method": {"method_key": "aashto_cda", "method_parameters": {}},
        "output": {
            "output_json_path": str(out_path),
            "overwrite": True,
        },
    }
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec))
    run_analysis_from_spec_file(p)
    return json.loads(out_path.read_text())


def _data_range(route_result: dict) -> dict:
    return route_result["input_data_analysis"]["data_summary"]["data_range"]


def test_x_min_boundary_row_is_kept(tmp_path: Path) -> None:
    """Row at exactly x_min must be included (>= not >)."""
    result = _run_spec_file(tmp_path, x_min=_BOUNDARY_X)
    for rr in result["route_results"]:
        assert _data_range(rr)["x_min"] >= _BOUNDARY_X


def test_x_max_boundary_row_is_kept(tmp_path: Path) -> None:
    """Row at exactly x_max must be included (<= not <)."""
    result = _run_spec_file(tmp_path, x_max=_BOUNDARY_X)
    for rr in result["route_results"]:
        assert _data_range(rr)["x_max"] <= _BOUNDARY_X


def test_x_min_excludes_rows_below_threshold(tmp_path: Path) -> None:
    """No analyzed data point should have x < x_min."""
    cutoff = 0.3
    result = _run_spec_file(tmp_path, x_min=cutoff)
    for rr in result["route_results"]:
        assert _data_range(rr)["x_min"] >= cutoff


def test_x_max_excludes_rows_above_threshold(tmp_path: Path) -> None:
    """No analyzed data point should have x > x_max."""
    cutoff = 0.3
    result = _run_spec_file(tmp_path, x_max=cutoff)
    for rr in result["route_results"]:
        assert _data_range(rr)["x_max"] <= cutoff


def test_x_range_empty_single_route_raises_specific_error(tmp_path: Path) -> None:
    """x_min beyond data range in single-route mode raises RunSpecError with x-range message."""
    from cli_runner import run_analysis_from_spec_file, RunSpecError

    spec = {
        "spec_version": "1.0.0",
        "input": {
            "data_file_path": _TEST_CSV,
            "x_column": "BDFO",
            "y_column": "SCI",
            "gap_threshold": 50.0,
            "x_min": 99999.0,
        },
        "method": {"method_key": "aashto_cda", "method_parameters": {}},
        "output": {
            "output_json_path": str(tmp_path / "out.json"),
            "overwrite": True,
        },
    }
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec))
    with pytest.raises(RunSpecError, match="No data remains within x-range"):
        run_analysis_from_spec_file(p)
