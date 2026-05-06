from __future__ import annotations

import json
from pathlib import Path

import pytest

import cli


@pytest.mark.file_io
def test_cli_validate_spec_ok(tmp_path: Path, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    fixture = repo_root / "tests" / "fixtures" / "run_spec_minimal.json"

    rc = cli.main(["validate-spec", "--spec", str(fixture)])
    assert rc == 0

    out = capsys.readouterr().out
    assert "OK" in out


@pytest.mark.file_io
def test_cli_run_writes_output(tmp_path: Path, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]

    spec = {
        "spec_version": "1.0.0",
        "input": {
            "data_file_path": str(repo_root / "data" / "test_data_single_route.csv"),
            "x_column": "milepoint",
            "y_column": "structural_strength_ind",
            "gap_threshold": 0.5,
        },
        "method": {"method_key": "aashto_cda", "method_parameters": {}},
        "output": {"output_json_path": str(tmp_path / "results.json"), "overwrite": True},
    }

    spec_path = tmp_path / "run_spec.json"
    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")

    rc = cli.main(["run", "--spec", str(spec_path), "--quiet"])
    assert rc == 0

    out = capsys.readouterr().out.strip()
    assert out.endswith("results.json")
    assert (tmp_path / "results.json").exists()
