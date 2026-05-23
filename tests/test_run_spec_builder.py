from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from run_spec import (
    build_batch_manifest,
    build_command_for_batch_run,
    build_command_for_run_spec,
    build_run_spec,
    default_batch_manifest_path,
    default_batch_output_dir,
    default_batch_run_spec_path,
    default_batch_summary_path,
)


def test_build_run_spec_validates_against_schema() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    schema_path = repo_root / "src" / "highway_segmentation_run_spec_schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    spec = build_run_spec(
        data_file_path="data/test.csv",
        x_column="milepoint",
        y_column="structural_strength_ind",
        gap_threshold=0.5,
        route_column=None,
        selected_routes=None,
        method_key="aashto_cda",
        method_parameters={},
        output_json_path="Results/out.json",
        overwrite=True,
        application_version="test",
    )

    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = sorted(validator.iter_errors(spec), key=lambda e: e.json_path)
    assert errors == [], "\n".join([f"{e.json_path}: {e.message}" for e in errors])


def test_build_run_spec_accepts_must_break_columns() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    schema_path = repo_root / "src" / "highway_segmentation_run_spec_schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    spec = build_run_spec(
        data_file_path="data/test.csv",
        x_column="milepoint",
        y_column="structural_strength_ind",
        gap_threshold=0.5,
        must_break_columns=["district", "pavement_type"],
        route_column=None,
        selected_routes=None,
        method_key="aashto_cda",
        method_parameters={},
        output_json_path="Results/out.json",
        overwrite=True,
        application_version="test",
    )

    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = sorted(validator.iter_errors(spec), key=lambda e: e.json_path)
    assert errors == [], "\n".join([f"{e.json_path}: {e.message}" for e in errors])


def test_build_command_for_run_spec_quotes_path() -> None:
    cmd = build_command_for_run_spec(r"C:\path with spaces\run_spec.json")
    assert "--spec" in cmd
    assert '"C:\\path with spaces\\run_spec.json"' in cmd


# ---------------------------------------------------------------------------
# Batch path default helpers
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_default_batch_run_spec_path_derives_template_suffix() -> None:
    result = default_batch_run_spec_path("Results/network_analysis.json")
    assert result == Path("Results/network_analysis.batch_template.run_spec.json")


@pytest.mark.unit
def test_default_batch_output_dir_appends_batch_suffix() -> None:
    result = default_batch_output_dir("Results/network_analysis.json")
    assert result == Path("Results/network_analysis_batch")


@pytest.mark.unit
def test_default_batch_manifest_path_derives_manifest_suffix() -> None:
    result = default_batch_manifest_path("Results/network_analysis.json")
    assert result == Path("Results/network_analysis.batch_manifest.json")


@pytest.mark.unit
def test_default_batch_summary_path_places_inside_output_dir() -> None:
    result = default_batch_summary_path("Results/network_analysis_batch")
    assert result == Path("Results/network_analysis_batch/batch_summary.json")


@pytest.mark.unit
def test_batch_path_helpers_accept_pathlib_objects() -> None:
    base = Path("Results/my_run.json")
    assert default_batch_run_spec_path(base).name == "my_run.batch_template.run_spec.json"
    assert default_batch_output_dir(base).name == "my_run_batch"
    assert default_batch_manifest_path(base).name == "my_run.batch_manifest.json"


# ---------------------------------------------------------------------------
# build_batch_manifest
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_build_batch_manifest_required_fields() -> None:
    manifest = build_batch_manifest(
        run_spec_path="Results/t.batch_template.run_spec.json",
        input_dir="data/incoming",
        glob="*.csv",
        recurse=False,
        output_dir="Results/t_batch",
        summary_json="Results/t_batch/batch_summary.json",
    )
    assert manifest["manifest_version"] == "1.0.0"
    assert manifest["run_spec_path"] == "Results/t.batch_template.run_spec.json"
    assert manifest["input_dir"] == "data/incoming"
    assert manifest["glob"] == "*.csv"
    assert manifest["recurse"] is False
    assert manifest["output_dir"] == "Results/t_batch"
    assert manifest["summary_json"] == "Results/t_batch/batch_summary.json"
    assert manifest["continue_on_error"] is True
    assert manifest["export_excel"] is False
    assert "created_at" in manifest
    assert manifest["created_by"]["application"] == "Highway Segmentation"


@pytest.mark.unit
def test_build_batch_manifest_optional_flags() -> None:
    manifest = build_batch_manifest(
        run_spec_path="r.json",
        input_dir="d",
        glob="*.csv",
        recurse=True,
        output_dir="out",
        summary_json="out/batch_summary.json",
        continue_on_error=False,
        export_excel=True,
        application_version="1.2.3",
    )
    assert manifest["recurse"] is True
    assert manifest["continue_on_error"] is False
    assert manifest["export_excel"] is True
    assert manifest["created_by"]["version"] == "1.2.3"


@pytest.mark.unit
def test_build_batch_manifest_accepts_fixed_created_at() -> None:
    ts = "2026-05-22T12:00:00Z"
    manifest = build_batch_manifest(
        run_spec_path="r.json",
        input_dir="d",
        glob="*.csv",
        recurse=False,
        output_dir="out",
        summary_json="out/s.json",
        created_at=ts,
    )
    assert manifest["created_at"] == ts


# ---------------------------------------------------------------------------
# build_command_for_batch_run
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_build_command_for_batch_run_contains_required_args() -> None:
    cmd = build_command_for_batch_run(
        "Results/t.batch_template.run_spec.json",
        "data/incoming",
        "Results/t_batch",
    )
    assert "run-batch" in cmd
    assert '--spec "Results/t.batch_template.run_spec.json"' in cmd
    assert '--input-dir "data/incoming"' in cmd
    assert '--output-dir "Results/t_batch"' in cmd
    assert '--glob "*.csv"' in cmd
    assert "--summary-json" in cmd


@pytest.mark.unit
def test_build_command_for_batch_run_defaults_summary_json() -> None:
    cmd = build_command_for_batch_run("s.json", "d", "Results/out")
    assert '"Results/out/batch_summary.json"' in cmd


@pytest.mark.unit
def test_build_command_for_batch_run_recurse_flag() -> None:
    cmd_no = build_command_for_batch_run("s.json", "d", "out", recurse=False)
    cmd_yes = build_command_for_batch_run("s.json", "d", "out", recurse=True)
    assert "--recurse" not in cmd_no
    assert "--recurse" in cmd_yes


@pytest.mark.unit
def test_build_command_for_batch_run_stop_on_error_flag() -> None:
    cmd_continue = build_command_for_batch_run("s.json", "d", "out", continue_on_error=True)
    cmd_stop = build_command_for_batch_run("s.json", "d", "out", continue_on_error=False)
    assert "--stop-on-error" not in cmd_continue
    assert "--stop-on-error" in cmd_stop


@pytest.mark.unit
def test_build_command_for_batch_run_export_excel_flag() -> None:
    cmd_no = build_command_for_batch_run("s.json", "d", "out", export_excel=False)
    cmd_yes = build_command_for_batch_run("s.json", "d", "out", export_excel=True)
    assert "--export-excel" not in cmd_no
    assert "--export-excel" in cmd_yes


@pytest.mark.unit
def test_build_command_for_batch_run_quotes_paths_with_spaces() -> None:
    cmd = build_command_for_batch_run(
        r"C:\My Results\spec.json",
        r"C:\My Data",
        r"C:\My Results\batch",
    )
    assert '"C:\\My Results\\spec.json"' in cmd
    assert '"C:\\My Data"' in cmd
    assert '"C:\\My Results\\batch"' in cmd
