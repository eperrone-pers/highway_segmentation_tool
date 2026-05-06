"""CLI regression suite.

This module mirrors the GUI/OptimizationController regression coverage, but runs
through the CLI run-spec pipeline:
- build run spec JSON using the regression parameter template
- execute `python src/cli.py run --spec ...` via `cli.main()` (no subprocess)
- validate results JSON structure and schema compliance

Goal: ensure headless execution stays equivalent to GUI execution for the same
method+dataset combinations.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict

import pytest

import cli
from run_spec import build_run_spec

from tests.regression.regression_matrix import (
    get_dataset_config,
    get_methods_and_datasets_from_template,
)

METHODS_TO_TEST, DATASETS_TO_TEST = get_methods_and_datasets_from_template()


def validate_json_structure(json_data: Dict[str, Any], method_key: str) -> None:
    assert isinstance(json_data, dict), "JSON data should be a dictionary"
    assert "analysis_metadata" in json_data, "Missing analysis_metadata"
    assert "input_parameters" in json_data, "Missing input_parameters"
    assert "route_results" in json_data, "Missing route_results"

    metadata = json_data["analysis_metadata"]
    assert metadata.get("analysis_method") == method_key

    opt_config = (json_data.get("input_parameters") or {}).get("optimization_method_config") or {}
    assert opt_config.get("method_key") == method_key


def validate_json_against_schema(json_data: Dict[str, Any]) -> None:
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


def _build_method_parameters(test_parameters: Dict[str, Any], method_key: str) -> Dict[str, Any]:
    common = dict(test_parameters.get("common_parameters", {}) or {})
    method_specific = dict((test_parameters.get("method_specific", {}) or {}).get(method_key, {}) or {})

    # Gap threshold belongs to the run-spec input section, not method parameters.
    common.pop("gap_threshold", None)

    merged = dict(common)
    merged.update(method_specific)
    return merged


@pytest.mark.parametrize("method_key", METHODS_TO_TEST)
@pytest.mark.parametrize("dataset", DATASETS_TO_TEST)
@pytest.mark.file_io
def test_cli_complete_workflow_matches_schema(method_key: str, dataset: str, test_parameters, tmp_path: Path) -> None:
    ds_conf = get_dataset_config(dataset)

    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "tests" / "test_data"

    data_file = data_dir / ds_conf["file"]
    if not data_file.exists():
        pytest.skip(f"Test data not found: {data_file}")

    x_col = ds_conf["x_column"]
    y_col = ds_conf["y_column"]
    route_col = ds_conf.get("route_column")

    gap_threshold = float((test_parameters.get("common_parameters", {}) or {}).get("gap_threshold", 0.5))

    output_json = tmp_path / f"cli_regression_{method_key}_{dataset}.json"
    spec_path = tmp_path / f"cli_regression_{method_key}_{dataset}.run_spec.json"

    spec = build_run_spec(
        data_file_path=str(data_file),
        x_column=x_col,
        y_column=y_col,
        gap_threshold=gap_threshold,
        route_column=route_col,
        selected_routes=None,
        method_key=method_key,
        method_parameters=_build_method_parameters(test_parameters, method_key),
        output_json_path=str(output_json),
        overwrite=True,
        application_version="regression-test",
    )

    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")

    # Run via the CLI entrypoint (command-line equivalent) without spawning subprocesses.
    rc = cli.main(["run", "--spec", str(spec_path), "--quiet"])
    assert rc == 0

    assert output_json.exists(), f"Expected CLI to write results JSON: {output_json}"
    json_data = json.loads(output_json.read_text(encoding="utf-8"))

    # Persist results for inspection alongside GUI regression artifacts, but with a distinct filename.
    # (Do NOT persist the run spec into outputs/json/ because other regression checks glob *.json there.)
    persistent_dir = Path(__file__).parent / "outputs" / "json"
    persistent_dir.mkdir(parents=True, exist_ok=True)
    persistent_json = persistent_dir / f"cli_regression_{method_key}_{dataset}.json"
    shutil.copy2(output_json, persistent_json)

    # Keep the same validation semantics as the existing regression suite.
    validate_json_structure(json_data, method_key)
    validate_json_against_schema(json_data)
