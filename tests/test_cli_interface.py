from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import cli
from run_spec import build_run_spec


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


# ---------------------------------------------------------------------------
# run-batch CLI tests
# ---------------------------------------------------------------------------

def _write_batch_spec(tmp_path: Path) -> Path:
    dummy_csv = tmp_path / "dummy.csv"
    dummy_csv.write_text("x,y\n1,2")
    spec = build_run_spec(
        data_file_path=str(dummy_csv),
        x_column="x",
        y_column="y",
        gap_threshold=0.5,
        method_key="aashto_cda",
        method_parameters={},
        output_json_path=str(tmp_path / "out.json"),
        application_version="test",
    )
    path = tmp_path / "template.run_spec.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


def _fake_runner(spec, *, log_callback=None):
    out = spec.output_json_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('{"mock": true}', encoding="utf-8")
    return str(out)


@pytest.mark.unit
def test_cli_run_batch_mode_missing_output_dir_exits_nonzero(tmp_path, capsys):
    spec_path = _write_batch_spec(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["run", "--spec", str(spec_path), "--input-dir", str(tmp_path)])
    assert exc_info.value.code != 0


@pytest.mark.unit
def test_cli_run_batch_bad_input_dir_returns_2(tmp_path, capsys):
    spec_path = _write_batch_spec(tmp_path)
    rc = cli.main([
        "run",
        "--spec", str(spec_path),
        "--input-dir", str(tmp_path / "nonexistent"),
        "--output-dir", str(tmp_path / "out"),
        "--no-validate-spec",
    ])
    assert rc == 2


@pytest.mark.unit
def test_cli_run_batch_success_returns_0_and_prints_summary_path(tmp_path, capsys):
    spec_path = _write_batch_spec(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    (data / "a.csv").write_text("x,y\n1,2")

    with patch("cli_runner._run_analysis_from_resolved_spec", side_effect=_fake_runner):
        rc = cli.main([
            "run",
            "--spec", str(spec_path),
            "--input-dir", str(data),
            "--output-dir", str(tmp_path / "out"),
            "--no-validate-spec",
            "--quiet",
        ])

    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert out.endswith("batch_summary.json")


@pytest.mark.unit
def test_cli_run_batch_partial_failure_returns_1(tmp_path, capsys):
    spec_path = _write_batch_spec(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    (data / "a.csv").write_text("x,y\n1,2")

    from cli_runner import RunSpecError

    def _always_fail(spec, *, log_callback=None):
        raise RunSpecError("simulated")

    with patch("cli_runner._run_analysis_from_resolved_spec", side_effect=_always_fail):
        rc = cli.main([
            "run",
            "--spec", str(spec_path),
            "--input-dir", str(data),
            "--output-dir", str(tmp_path / "out"),
            "--no-validate-spec",
            "--quiet",
        ])

    assert rc == 1
