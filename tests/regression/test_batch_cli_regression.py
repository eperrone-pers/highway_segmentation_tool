"""Regression tests for the run-batch CLI pipeline.

Uses dedicated synthetic CSV fixtures in tests/test_data/batch_cli/ — small
two-segment datasets that run fast but exercise all code paths in the batch runner.

Each scenario (flat, recurse, custom summary path, excel export) is executed
once via a module-scoped fixture; individual test functions assert specific
invariants without re-running analysis.

Marked regression + file_io (all tests in this folder also inherit regression
via the regression conftest auto-marker).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import cli
from run_spec import build_run_spec


REPO_ROOT = Path(__file__).resolve().parents[2]
BATCH_DATA_DIR = REPO_ROOT / "tests" / "test_data" / "batch_cli"
RESULTS_SCHEMA_PATH = REPO_ROOT / "src" / "highway_segmentation_results_schema.json"

def _silent(_: str) -> None:
    pass

FLAT_FILES = {"route_north.csv", "route_south.csv", "route_east.csv"}
ALL_FILES = FLAT_FILES | {"route_west.csv"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_template_spec(tmp_path: Path) -> Path:
    """Write a template run spec using the batch_cli column layout."""
    spec = build_run_spec(
        data_file_path=str(BATCH_DATA_DIR / "route_north.csv"),
        x_column="milepoint",
        y_column="structural_strength_ind",
        gap_threshold=0.5,
        method_key="aashto_cda",
        method_parameters={},
        output_json_path=str(tmp_path / "placeholder.json"),
        application_version="regression-test",
    )
    path = tmp_path / "batch_template.run_spec.json"
    path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return path


def _validate_result_json_structure(data: dict) -> None:
    assert "analysis_metadata" in data, "Missing analysis_metadata"
    assert "input_parameters" in data, "Missing input_parameters"
    assert "route_results" in data, "Missing route_results"
    assert isinstance(data["route_results"], list), "route_results must be a list"
    assert len(data["route_results"]) >= 1, "Expected at least one route result"


def _validate_against_results_schema(data: dict) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        pytest.skip("jsonschema not installed")

    schema = json.loads(RESULTS_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.json_path)
    assert errors == [], "\n".join(f"{e.json_path}: {e.message}" for e in errors)


# ---------------------------------------------------------------------------
# Module-scoped fixtures — run each CLI scenario once
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def flat_run(tmp_path_factory):
    """Batch run against the 3 flat CSVs (no recurse)."""
    tmp = tmp_path_factory.mktemp("flat")
    spec = _build_template_spec(tmp)
    out = tmp / "results"
    rc = cli.main([
        "run",
        "--spec", str(spec),
        "--input-dir", str(BATCH_DATA_DIR),
        "--output-dir", str(out),
        "--quiet",
    ])
    summary_path = out / "batch_summary.json"
    return {
        "rc": rc,
        "out": out,
        "summary": json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {},
    }


@pytest.fixture(scope="module")
def recurse_run(tmp_path_factory):
    """Batch run with --recurse, picks up subdir/route_west.csv as well."""
    tmp = tmp_path_factory.mktemp("recurse")
    spec = _build_template_spec(tmp)
    out = tmp / "results"
    rc = cli.main([
        "run",
        "--spec", str(spec),
        "--input-dir", str(BATCH_DATA_DIR),
        "--output-dir", str(out),
        "--recurse",
        "--quiet",
    ])
    summary_path = out / "batch_summary.json"
    return {
        "rc": rc,
        "out": out,
        "summary": json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {},
    }


@pytest.fixture(scope="module")
def custom_summary_run(tmp_path_factory):
    """Batch run with a user-specified --summary-json path."""
    tmp = tmp_path_factory.mktemp("custom_summary")
    spec = _build_template_spec(tmp)
    out = tmp / "results"
    custom_summary = tmp / "my_batch_summary.json"
    rc = cli.main([
        "run",
        "--spec", str(spec),
        "--input-dir", str(BATCH_DATA_DIR),
        "--output-dir", str(out),
        "--summary-json", str(custom_summary),
        "--quiet",
    ])
    return {
        "rc": rc,
        "out": out,
        "custom_summary_path": custom_summary,
    }


@pytest.fixture(scope="module")
def excel_run(tmp_path_factory):
    """Batch run with --export-excel."""
    tmp = tmp_path_factory.mktemp("excel")
    spec = _build_template_spec(tmp)
    out = tmp / "results"
    rc = cli.main([
        "run",
        "--spec", str(spec),
        "--input-dir", str(BATCH_DATA_DIR),
        "--output-dir", str(out),
        "--export-excel",
        "--quiet",
    ])
    return {"rc": rc, "out": out}


# ---------------------------------------------------------------------------
# Flat run assertions
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.file_io
def test_flat_run_exits_zero(flat_run):
    assert flat_run["rc"] == 0


@pytest.mark.regression
@pytest.mark.file_io
def test_flat_run_produces_result_json_for_each_input(flat_run):
    for stem in ["route_north", "route_south", "route_east"]:
        assert (flat_run["out"] / f"{stem}.json").exists(), f"Missing {stem}.json"


@pytest.mark.regression
@pytest.mark.file_io
def test_flat_run_does_not_include_subdir_file(flat_run):
    assert not (flat_run["out"] / "route_west.json").exists()


@pytest.mark.regression
@pytest.mark.file_io
def test_flat_run_summary_counts_three_files(flat_run):
    s = flat_run["summary"]
    assert s["total_files"] == 3
    assert s["completed"] == 3
    assert s["failed"] == 0


@pytest.mark.regression
@pytest.mark.file_io
def test_flat_run_summary_all_results_success(flat_run):
    assert all(r["status"] == "success" for r in flat_run["summary"]["results"])


@pytest.mark.regression
@pytest.mark.file_io
def test_flat_run_summary_has_timestamps(flat_run):
    s = flat_run["summary"]
    assert "started_at" in s and s["started_at"]
    assert "finished_at" in s and s["finished_at"]


# ---------------------------------------------------------------------------
# Per-file result JSON structure (using flat_run)
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.file_io
@pytest.mark.parametrize("stem", ["route_north", "route_south", "route_east"])
def test_result_json_has_standard_structure(flat_run, stem):
    data = json.loads((flat_run["out"] / f"{stem}.json").read_text(encoding="utf-8"))
    _validate_result_json_structure(data)


@pytest.mark.regression
@pytest.mark.file_io
@pytest.mark.parametrize("stem", ["route_north", "route_south", "route_east"])
def test_result_json_validates_against_results_schema(flat_run, stem):
    data = json.loads((flat_run["out"] / f"{stem}.json").read_text(encoding="utf-8"))
    _validate_against_results_schema(data)


@pytest.mark.regression
@pytest.mark.file_io
@pytest.mark.parametrize("stem", ["route_north", "route_south", "route_east"])
def test_result_json_method_key_is_aashto_cda(flat_run, stem):
    data = json.loads((flat_run["out"] / f"{stem}.json").read_text(encoding="utf-8"))
    assert data["analysis_metadata"]["analysis_method"] == "aashto_cda"


# ---------------------------------------------------------------------------
# Recurse run assertions
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.file_io
def test_recurse_run_exits_zero(recurse_run):
    assert recurse_run["rc"] == 0


@pytest.mark.regression
@pytest.mark.file_io
def test_recurse_run_includes_subdir_file(recurse_run):
    assert (recurse_run["out"] / "route_west.json").exists()


@pytest.mark.regression
@pytest.mark.file_io
def test_recurse_run_summary_counts_four_files(recurse_run):
    s = recurse_run["summary"]
    assert s["total_files"] == 4
    assert s["completed"] == 4
    assert s["failed"] == 0


# ---------------------------------------------------------------------------
# Custom summary path
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.file_io
def test_custom_summary_path_exits_zero(custom_summary_run):
    assert custom_summary_run["rc"] == 0


@pytest.mark.regression
@pytest.mark.file_io
def test_custom_summary_written_to_specified_path(custom_summary_run):
    assert custom_summary_run["custom_summary_path"].exists()


@pytest.mark.regression
@pytest.mark.file_io
def test_custom_summary_default_location_not_created(custom_summary_run):
    assert not (custom_summary_run["out"] / "batch_summary.json").exists()


# ---------------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.file_io
def test_excel_run_exits_zero(excel_run):
    assert excel_run["rc"] == 0


@pytest.mark.regression
@pytest.mark.file_io
@pytest.mark.parametrize("stem", ["route_north", "route_south", "route_east"])
def test_excel_run_produces_xlsx_alongside_json(excel_run, stem):
    assert (excel_run["out"] / f"{stem}.json").exists(), f"Missing {stem}.json"
    assert (excel_run["out"] / f"{stem}.xlsx").exists(), f"Missing {stem}.xlsx"
