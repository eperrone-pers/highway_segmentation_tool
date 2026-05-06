from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from run_spec import build_command_for_run_spec, build_run_spec


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


def test_build_command_for_run_spec_quotes_path() -> None:
    cmd = build_command_for_run_spec(r"C:\path with spaces\run_spec.json")
    assert "--spec" in cmd
    assert '"C:\\path with spaces\\run_spec.json"' in cmd
