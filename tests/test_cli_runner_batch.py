"""Unit tests for the batch runner helpers in cli_runner.py.

All tests that invoke ``run_batch_analysis_from_spec_file`` patch out
``_run_analysis_from_resolved_spec`` so no real analysis runs — these are
fast, filesystem-only tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cli_runner import (
    BatchPartialFailureError,
    RunSpecError,
    _detect_stem_collisions,
    discover_batch_input_files,
    run_batch_analysis_from_spec_file,
)
from run_spec import build_run_spec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_template_spec(tmp_path: Path, data_file: Path) -> Path:
    spec = build_run_spec(
        data_file_path=str(data_file),
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
    """Mock inner runner — writes a stub JSON and returns its absolute path."""
    out = spec.output_json_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('{"mock": true}', encoding="utf-8")
    return str(out)


# ---------------------------------------------------------------------------
# discover_batch_input_files
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_discover_batch_finds_csvs_in_flat_dir(tmp_path):
    (tmp_path / "a.csv").write_text("x,y\n1,2")
    (tmp_path / "b.csv").write_text("x,y\n3,4")
    result = discover_batch_input_files(tmp_path, "*.csv", recurse=False)
    assert {f.name for f in result} == {"a.csv", "b.csv"}


@pytest.mark.unit
def test_discover_batch_flat_excludes_subdirectories(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.csv").write_text("x,y\n1,2")
    result = discover_batch_input_files(tmp_path, "*.csv", recurse=False)
    assert result == []


@pytest.mark.unit
def test_discover_batch_recurse_finds_nested_files(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.csv").write_text("x,y\n1,2")
    (tmp_path / "sub" / "b.csv").write_text("x,y\n3,4")
    result = discover_batch_input_files(tmp_path, "*.csv", recurse=True)
    assert {f.name for f in result} == {"a.csv", "b.csv"}


@pytest.mark.unit
def test_discover_batch_ignores_non_matching_extensions(tmp_path):
    (tmp_path / "a.csv").write_text("x,y\n1,2")
    (tmp_path / "b.xlsx").write_text("ignored")
    result = discover_batch_input_files(tmp_path, "*.csv", recurse=False)
    assert len(result) == 1 and result[0].name == "a.csv"


@pytest.mark.unit
def test_discover_batch_returns_sorted(tmp_path):
    for name in ["z.csv", "a.csv", "m.csv"]:
        (tmp_path / name).write_text("x,y\n1,2")
    result = discover_batch_input_files(tmp_path, "*.csv", recurse=False)
    assert [f.name for f in result] == ["a.csv", "m.csv", "z.csv"]


# ---------------------------------------------------------------------------
# _detect_stem_collisions
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_detect_stem_collisions_empty_when_unique():
    files = [Path("/d/a.csv"), Path("/d/b.csv")]
    assert _detect_stem_collisions(files) == []


@pytest.mark.unit
def test_detect_stem_collisions_finds_duplicate():
    files = [
        Path("/dir1/route.csv"),
        Path("/dir2/route.csv"),
        Path("/dir3/other.csv"),
    ]
    assert _detect_stem_collisions(files) == ["route"]


@pytest.mark.unit
def test_detect_stem_collisions_returns_sorted():
    files = [
        Path("/x/z.csv"),
        Path("/y/z.csv"),
        Path("/a/m.csv"),
        Path("/b/m.csv"),
    ]
    assert _detect_stem_collisions(files) == ["m", "z"]


@pytest.mark.unit
def test_detect_stem_collisions_empty_input():
    assert _detect_stem_collisions([]) == []


# ---------------------------------------------------------------------------
# Hard errors — no real analysis, no mock needed
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_run_batch_raises_when_input_dir_missing(tmp_path):
    dummy_spec = tmp_path / "t.json"
    dummy_spec.write_text("{}")
    with pytest.raises(RunSpecError, match="does not exist"):
        run_batch_analysis_from_spec_file(
            dummy_spec,
            tmp_path / "nonexistent",
            tmp_path / "out",
            validate_spec=False,
        )


@pytest.mark.unit
def test_run_batch_raises_when_no_files_match(tmp_path):
    dummy_csv = tmp_path / "x.csv"
    dummy_csv.write_text("x,y\n1,2")
    spec_path = _write_template_spec(tmp_path, dummy_csv)
    data = tmp_path / "data"
    data.mkdir()
    with pytest.raises(RunSpecError, match="No files matching"):
        run_batch_analysis_from_spec_file(
            spec_path, data, tmp_path / "out", validate_spec=False
        )


@pytest.mark.unit
def test_run_batch_raises_on_stem_collision(tmp_path):
    dummy_csv = tmp_path / "x.csv"
    dummy_csv.write_text("x,y\n1,2")
    spec_path = _write_template_spec(tmp_path, dummy_csv)

    data = tmp_path / "data"
    data.mkdir()
    (data / "sub").mkdir()
    (data / "route.csv").write_text("x,y\n1,2")
    (data / "sub" / "route.csv").write_text("x,y\n3,4")

    with pytest.raises(RunSpecError, match="Stem collisions"):
        run_batch_analysis_from_spec_file(
            spec_path, data, tmp_path / "out", recurse=True, validate_spec=False
        )


# ---------------------------------------------------------------------------
# Mocked inner runner — summary structure and success path
# ---------------------------------------------------------------------------

@pytest.fixture
def batch_env(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "a.csv").write_text("x,y\n1,2")
    (data / "b.csv").write_text("x,y\n3,4")
    dummy_csv = tmp_path / "dummy.csv"
    dummy_csv.write_text("x,y\n1,2")
    spec_path = _write_template_spec(tmp_path, dummy_csv)
    return {"spec_path": spec_path, "data": data, "out": tmp_path / "out", "tmp": tmp_path}


@pytest.mark.unit
def test_run_batch_returns_summary_path_string(batch_env):
    with patch("cli_runner._run_analysis_from_resolved_spec", side_effect=_fake_runner):
        result = run_batch_analysis_from_spec_file(
            batch_env["spec_path"], batch_env["data"], batch_env["out"], validate_spec=False
        )
    assert isinstance(result, str)
    assert result.endswith("batch_summary.json")


@pytest.mark.unit
def test_run_batch_summary_file_exists(batch_env):
    with patch("cli_runner._run_analysis_from_resolved_spec", side_effect=_fake_runner):
        summary_path = run_batch_analysis_from_spec_file(
            batch_env["spec_path"], batch_env["data"], batch_env["out"], validate_spec=False
        )
    assert Path(summary_path).exists()


@pytest.mark.unit
def test_run_batch_summary_has_required_fields(batch_env):
    with patch("cli_runner._run_analysis_from_resolved_spec", side_effect=_fake_runner):
        summary_path = run_batch_analysis_from_spec_file(
            batch_env["spec_path"], batch_env["data"], batch_env["out"], validate_spec=False
        )
    summary = json.loads(Path(summary_path).read_text())
    assert summary["batch_version"] == "1.0.0"
    assert summary["total_files"] == 2
    assert summary["completed"] == 2
    assert summary["failed"] == 0
    assert len(summary["results"]) == 2
    assert "started_at" in summary
    assert "finished_at" in summary


@pytest.mark.unit
def test_run_batch_all_results_marked_success(batch_env):
    with patch("cli_runner._run_analysis_from_resolved_spec", side_effect=_fake_runner):
        summary_path = run_batch_analysis_from_spec_file(
            batch_env["spec_path"], batch_env["data"], batch_env["out"], validate_spec=False
        )
    summary = json.loads(Path(summary_path).read_text())
    assert all(r["status"] == "success" for r in summary["results"])


@pytest.mark.unit
def test_run_batch_custom_summary_json_path(batch_env):
    custom = batch_env["tmp"] / "my_summary.json"
    with patch("cli_runner._run_analysis_from_resolved_spec", side_effect=_fake_runner):
        run_batch_analysis_from_spec_file(
            batch_env["spec_path"],
            batch_env["data"],
            batch_env["out"],
            summary_json=str(custom),
            validate_spec=False,
        )
    assert custom.exists()


# ---------------------------------------------------------------------------
# Error handling — continue vs stop
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_run_batch_continue_on_error_processes_all_files(batch_env):
    call_count = [0]

    def _flaky(spec, *, log_callback=None):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RunSpecError("simulated failure")
        return _fake_runner(spec, log_callback=log_callback)

    with patch("cli_runner._run_analysis_from_resolved_spec", side_effect=_flaky):
        with pytest.raises(BatchPartialFailureError):
            run_batch_analysis_from_spec_file(
                batch_env["spec_path"],
                batch_env["data"],
                batch_env["out"],
                continue_on_error=True,
                validate_spec=False,
            )

    assert call_count[0] == 2


@pytest.mark.unit
def test_run_batch_continue_on_error_summary_records_one_failure(batch_env):
    call_count = [0]

    def _flaky(spec, *, log_callback=None):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RunSpecError("simulated failure")
        return _fake_runner(spec, log_callback=log_callback)

    summary_json = batch_env["out"] / "batch_summary.json"
    with patch("cli_runner._run_analysis_from_resolved_spec", side_effect=_flaky):
        try:
            run_batch_analysis_from_spec_file(
                batch_env["spec_path"],
                batch_env["data"],
                batch_env["out"],
                summary_json=str(summary_json),
                continue_on_error=True,
                validate_spec=False,
            )
        except BatchPartialFailureError:
            pass

    summary = json.loads(summary_json.read_text())
    assert summary["failed"] == 1
    assert summary["completed"] == 1
    statuses = {r["status"] for r in summary["results"]}
    assert statuses == {"failed", "success"}


@pytest.mark.unit
def test_run_batch_raises_batch_partial_failure_error_type(batch_env):
    def _always_fail(spec, *, log_callback=None):
        raise RunSpecError("oops")

    with patch("cli_runner._run_analysis_from_resolved_spec", side_effect=_always_fail):
        with pytest.raises(BatchPartialFailureError):
            run_batch_analysis_from_spec_file(
                batch_env["spec_path"],
                batch_env["data"],
                batch_env["out"],
                continue_on_error=True,
                validate_spec=False,
            )


@pytest.mark.unit
def test_run_batch_stop_on_error_stops_after_first_failure(batch_env):
    call_count = [0]

    def _always_fail(spec, *, log_callback=None):
        call_count[0] += 1
        raise RunSpecError("simulated failure")

    with patch("cli_runner._run_analysis_from_resolved_spec", side_effect=_always_fail):
        with pytest.raises(RunSpecError):
            run_batch_analysis_from_spec_file(
                batch_env["spec_path"],
                batch_env["data"],
                batch_env["out"],
                continue_on_error=False,
                validate_spec=False,
            )

    assert call_count[0] == 1


@pytest.mark.unit
def test_run_batch_stop_on_error_writes_summary_before_raising(batch_env):
    summary_json = batch_env["out"] / "batch_summary.json"

    def _always_fail(spec, *, log_callback=None):
        raise RunSpecError("simulated failure")

    with patch("cli_runner._run_analysis_from_resolved_spec", side_effect=_always_fail):
        try:
            run_batch_analysis_from_spec_file(
                batch_env["spec_path"],
                batch_env["data"],
                batch_env["out"],
                summary_json=str(summary_json),
                continue_on_error=False,
                validate_spec=False,
            )
        except RunSpecError:
            pass

    assert summary_json.exists()


# ---------------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_run_batch_export_excel_calls_exporter_once_per_file(batch_env):
    with patch("cli_runner._run_analysis_from_resolved_spec", side_effect=_fake_runner):
        with patch("excel_export.export_json_to_excel", return_value=True) as mock_export:
            run_batch_analysis_from_spec_file(
                batch_env["spec_path"],
                batch_env["data"],
                batch_env["out"],
                export_excel=True,
                validate_spec=False,
            )
    assert mock_export.call_count == 2


@pytest.mark.unit
def test_run_batch_export_excel_false_never_calls_exporter(batch_env):
    with patch("cli_runner._run_analysis_from_resolved_spec", side_effect=_fake_runner):
        with patch("excel_export.export_json_to_excel", return_value=True) as mock_export:
            run_batch_analysis_from_spec_file(
                batch_env["spec_path"],
                batch_env["data"],
                batch_env["out"],
                export_excel=False,
                validate_spec=False,
            )
    mock_export.assert_not_called()
