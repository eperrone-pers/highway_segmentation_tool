from __future__ import annotations

import json
from pathlib import Path

import jsonschema


def test_run_spec_fixture_validates_against_schema() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    schema_path = repo_root / "src" / "highway_segmentation_run_spec_schema.json"
    fixture_path = repo_root / "tests" / "fixtures" / "run_spec_minimal.json"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    instance = json.loads(fixture_path.read_text(encoding="utf-8"))

    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.json_path)
    assert errors == [], "\n".join([f"{e.json_path}: {e.message}" for e in errors])


def test_run_spec_rejects_unknown_top_level_keys() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    schema_path = repo_root / "src" / "highway_segmentation_run_spec_schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    instance = {
        "spec_version": "1.0.0",
        "input": {
            "data_file_path": "data/test_data_single_route.csv",
            "x_column": "mile",
            "y_column": "value",
            "gap_threshold": 0.5,
        },
        "method": {"method_key": "multi", "method_parameters": {}},
        "output": {"output_json_path": "Results/out.json"},
        "typo_key_should_fail": True,
    }

    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = list(validator.iter_errors(instance))
    assert any("Additional properties" in e.message for e in errors)
