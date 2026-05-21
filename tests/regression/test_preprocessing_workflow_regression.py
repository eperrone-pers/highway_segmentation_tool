"""Preprocessing regression suite.

Validates end-to-end preprocessing workflows through the CLI pipeline:
- Tukey Fences outlier detection with remove/cap/interpolate actions
- Single route and multi-route datasets with injected outliers
- Complete workflow: preprocessing → optimization → JSON export → schema validation
- Ensures preprocessing metadata is correctly captured in results

Test Coverage:
    Methods: single (focus on preprocessing validation)
    Actions: remove, cap, interpolate
    Datasets: single_route_with_outliers, multi_route_with_outliers
    
Output Artifacts:
    JSON results: tests/regression/outputs/json/preprocessing_{action}_{dataset}.json
    
Schema Validation:
    - Validates preprocessing_summary field structure
    - Validates preprocessing_modification_log entries
    - Ensures schema compliance for all preprocessing metadata
    
Regression Detection:
    - Breaking changes in preprocessing API
    - Modification logging failures
    - JSON export format changes
    - Schema compliance violations
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict

import pytest

import cli
from run_spec import build_run_spec


def _load_regression_template() -> Dict[str, Any]:
    """Load the regression parameters template."""
    template_path = Path(__file__).parent / "test_parameters_template.json"
    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_json_structure(json_data: Dict[str, Any], method_key: str) -> None:
    """Validate basic JSON structure."""
    assert isinstance(json_data, dict), "JSON data should be a dictionary"
    assert "analysis_metadata" in json_data, "Missing analysis_metadata"
    assert "input_parameters" in json_data, "Missing input_parameters"
    assert "route_results" in json_data, "Missing route_results"
    
    metadata = json_data["analysis_metadata"]
    assert metadata.get("analysis_method") == method_key


def validate_preprocessing_metadata(json_data: Dict[str, Any]) -> None:
    """Validate preprocessing-specific metadata in results."""
    # Check preprocessing config in input_parameters
    input_params = json_data.get("input_parameters", {})
    preprocessing_config = input_params.get("preprocessing_config")
    assert preprocessing_config is not None, "Missing preprocessing_config in input_parameters"
    assert preprocessing_config.get("enabled") is True, "Preprocessing should be enabled"
    assert "primary_method" in preprocessing_config, "Missing primary_method"
    assert "primary_parameters" in preprocessing_config, "Missing primary_parameters"
    
    # Check preprocessing results in route_results
    route_results = json_data.get("route_results", [])
    assert len(route_results) > 0, "No route results found"
    
    for route_result in route_results:
        # Check preprocessing_summary (should be an object with phases array)
        preprocessing_summary = route_result.get("preprocessing_summary")
        assert preprocessing_summary is not None, f"Missing preprocessing_summary for route {route_result.get('route_id')}"
        assert isinstance(preprocessing_summary, dict), "preprocessing_summary should be a dict"
        assert "phases" in preprocessing_summary, "Missing phases in preprocessing_summary"
        assert "preprocessing_applied" in preprocessing_summary, "Missing preprocessing_applied in preprocessing_summary"
        assert preprocessing_summary["preprocessing_applied"] is True, "preprocessing_applied should be True"
        
        phases = preprocessing_summary["phases"]
        assert isinstance(phases, list), "phases should be a list"
        assert len(phases) > 0, "phases should have at least one phase"
        
        # Validate phase structure
        for phase in phases:
            assert "phase_name" in phase, "Missing phase_name field"
            assert "method_name" in phase, "Missing method_name"
            assert "points_before" in phase, "Missing points_before"
            assert "points_after" in phase, "Missing points_after"
        
        # Check preprocessing_modification_log
        modification_log = route_result.get("preprocessing_modification_log")
        assert modification_log is not None, f"Missing preprocessing_modification_log for route {route_result.get('route_id')}"
        assert isinstance(modification_log, list), "preprocessing_modification_log should be a list"
        
        # If modifications were made, validate log entries
        total_modifications = preprocessing_summary.get("total_modifications", 0)
        if total_modifications > 0:
            assert len(modification_log) > 0, "Expected modification log entries"
            
            # Validate first phase log structure
            phase_log = modification_log[0]
            assert isinstance(phase_log, list), "Phase log should be a list"
            
            if len(phase_log) > 0:
                mod = phase_log[0]
                assert "modification_type" in mod, "Missing modification_type"
                assert "x_value" in mod, "Missing x_value"
                assert "timestamp" in mod, "Missing timestamp"
                assert isinstance(mod["timestamp"], str), "timestamp should be ISO format string"


def validate_json_against_schema(json_data: Dict[str, Any]) -> None:
    """Validate JSON against official schema."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        pytest.skip("jsonschema not installed")
    
    repo_root = Path(__file__).resolve().parents[2]
    schema_path = repo_root / "src" / "highway_segmentation_results_schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(json_data), key=lambda e: e.json_path)
    assert errors == [], "\n".join([f"{e.json_path}: {e.message}" for e in errors])


# Test matrix: preprocessing actions × datasets with outliers
PREPROCESSING_ACTIONS = ["tukey_remove", "tukey_cap", "tukey_interpolate"]
DATASETS_WITH_OUTLIERS = ["single_route_with_outliers", "multi_route_with_outliers"]


@pytest.mark.parametrize("preprocessing_action", PREPROCESSING_ACTIONS)
@pytest.mark.parametrize("dataset", DATASETS_WITH_OUTLIERS)
@pytest.mark.file_io
def test_preprocessing_complete_workflow(
    preprocessing_action: str, 
    dataset: str, 
    test_parameters, 
    tmp_path: Path
) -> None:
    """Test complete preprocessing workflow with CLI execution."""
    template = _load_regression_template()
    
    # Get dataset configuration
    ds_conf = template["data_configurations"][dataset]
    preprocessing_conf = template["preprocessing_configurations"][preprocessing_action]
    
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "tests" / "test_data"
    
    data_file = data_dir / ds_conf["file"]
    if not data_file.exists():
        pytest.skip(f"Test data not found: {data_file}")
    
    x_col = ds_conf["x_column"]
    y_col = ds_conf["y_column"]
    route_col = ds_conf.get("route_column")
    
    gap_threshold = float((test_parameters.get("common_parameters", {}) or {}).get("gap_threshold", 0.5))
    
    # Use single method for preprocessing validation (focus is on preprocessing, not optimization)
    method_key = "single"
    method_params = dict(test_parameters.get("common_parameters", {}) or {})
    method_params.pop("gap_threshold", None)  # Move to run spec input section
    
    # Build preprocessing config
    preprocessing_config = {
        "enabled": True,
        "primary_method": preprocessing_conf["primary_method"],
        "primary_parameters": preprocessing_conf["primary_parameters"]
    }
    
    output_json = tmp_path / f"preprocessing_{preprocessing_action}_{dataset}.json"
    spec_path = tmp_path / f"preprocessing_{preprocessing_action}_{dataset}.run_spec.json"
    
    # Build run spec
    spec = build_run_spec(
        data_file_path=str(data_file),
        x_column=x_col,
        y_column=y_col,
        gap_threshold=gap_threshold,
        route_column=route_col,
        selected_routes=None,
        method_key=method_key,
        method_parameters=method_params,
        output_json_path=str(output_json),
        overwrite=True,
        application_version="preprocessing-regression-test",
    )
    
    # Add preprocessing configuration to spec
    spec["preprocessing"] = preprocessing_config
    
    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    
    # Run via CLI entrypoint
    rc = cli.main(["run", "--spec", str(spec_path), "--quiet"])
    assert rc == 0, f"CLI execution failed with return code {rc}"
    
    assert output_json.exists(), f"Expected CLI to write results JSON: {output_json}"
    json_data = json.loads(output_json.read_text(encoding="utf-8"))
    
    # Persist results for inspection
    persistent_dir = Path(__file__).parent / "outputs" / "json"
    persistent_dir.mkdir(parents=True, exist_ok=True)
    persistent_json = persistent_dir / f"preprocessing_{preprocessing_action}_{dataset}.json"
    shutil.copy2(output_json, persistent_json)
    
    # Validation
    validate_json_structure(json_data, method_key)
    validate_preprocessing_metadata(json_data)
    validate_json_against_schema(json_data)


@pytest.mark.file_io
def test_no_preprocessing_baseline(test_parameters, tmp_path: Path) -> None:
    """Baseline test with no preprocessing to ensure backward compatibility."""
    template = _load_regression_template()
    
    # Use clean single route data (no outliers)
    ds_conf = template["data_configurations"]["single_route"]
    
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "tests" / "test_data"
    
    data_file = data_dir / ds_conf["file"]
    if not data_file.exists():
        pytest.skip(f"Test data not found: {data_file}")
    
    x_col = ds_conf["x_column"]
    y_col = ds_conf["y_column"]
    route_col = ds_conf.get("route_column")
    
    gap_threshold = float((test_parameters.get("common_parameters", {}) or {}).get("gap_threshold", 0.5))
    
    method_key = "single"
    method_params = dict(test_parameters.get("common_parameters", {}) or {})
    method_params.pop("gap_threshold", None)
    
    output_json = tmp_path / "preprocessing_baseline_no_preprocessing.json"
    spec_path = tmp_path / "preprocessing_baseline_no_preprocessing.run_spec.json"
    
    # Build run spec WITHOUT preprocessing
    spec = build_run_spec(
        data_file_path=str(data_file),
        x_column=x_col,
        y_column=y_col,
        gap_threshold=gap_threshold,
        route_column=route_col,
        selected_routes=None,
        method_key=method_key,
        method_parameters=method_params,
        output_json_path=str(output_json),
        overwrite=True,
        application_version="preprocessing-regression-test",
    )
    
    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    
    # Run via CLI
    rc = cli.main(["run", "--spec", str(spec_path), "--quiet"])
    assert rc == 0
    
    assert output_json.exists()
    json_data = json.loads(output_json.read_text(encoding="utf-8"))
    
    # Persist baseline results
    persistent_dir = Path(__file__).parent / "outputs" / "json"
    persistent_dir.mkdir(parents=True, exist_ok=True)
    persistent_json = persistent_dir / "preprocessing_baseline_no_preprocessing.json"
    shutil.copy2(output_json, persistent_json)
    
    # Validate basic structure (no preprocessing metadata expected)
    validate_json_structure(json_data, method_key)
    validate_json_against_schema(json_data)
    
    # Verify NO preprocessing metadata in results (backward compatibility)
    route_results = json_data.get("route_results", [])
    for route_result in route_results:
        # These fields should not exist or be null when preprocessing is disabled
        preprocessing_summary = route_result.get("preprocessing_summary")
        assert preprocessing_summary is None or preprocessing_summary == [], \
            "preprocessing_summary should be absent or empty when preprocessing is disabled"
