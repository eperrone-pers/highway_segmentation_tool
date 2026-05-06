from __future__ import annotations

import json
from pathlib import Path

import pytest

from cli_runner import run_analysis_from_spec_file


@pytest.mark.file_io
def test_run_analysis_from_spec_file_writes_results_json(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]

    spec = {
        "spec_version": "1.0.0",
        "input": {
            "data_file_path": str(repo_root / "data" / "test_data_single_route.csv"),
            "x_column": "milepoint",
            "y_column": "structural_strength_ind",
            "gap_threshold": 0.5,
            "route_column": None,
            "selected_routes": None,
        },
        "method": {
            "method_key": "aashto_cda",
            "method_parameters": {
                # Keep runs deterministic and fast via defaults.
            },
        },
        "output": {
            "output_json_path": str(tmp_path / "results.json"),
            "overwrite": True,
        },
    }

    spec_path = tmp_path / "run_spec.json"
    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")

    output_path = run_analysis_from_spec_file(spec_path, validate_spec=True, log_callback=lambda _: None)
    out = Path(output_path)

    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))

    assert "analysis_metadata" in data
    assert "input_parameters" in data
    assert "route_results" in data


@pytest.mark.file_io
def test_overwrite_false_rejects_existing_output(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]

    out_path = tmp_path / "results.json"
    out_path.write_text("{}", encoding="utf-8")

    spec = {
        "spec_version": "1.0.0",
        "input": {
            "data_file_path": str(repo_root / "data" / "test_data_single_route.csv"),
            "x_column": "milepoint",
            "y_column": "structural_strength_ind",
            "gap_threshold": 0.5,
        },
        "method": {"method_key": "aashto_cda", "method_parameters": {}},
        "output": {"output_json_path": str(out_path), "overwrite": False},
    }

    spec_path = tmp_path / "run_spec.json"
    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")

    with pytest.raises(Exception) as excinfo:
        run_analysis_from_spec_file(spec_path, validate_spec=True, log_callback=lambda _: None)

    assert "overwrite=false" in str(excinfo.value)
