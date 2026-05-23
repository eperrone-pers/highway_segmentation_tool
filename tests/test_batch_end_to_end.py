"""End-to-end integration tests for the run-batch pipeline.

Tests run real analysis (no mocking) against actual CSV fixtures to verify the
full chain: dialog-style artifact generation → CLI → per-file results + summary.

Marked file_io because they read real CSV fixtures and write to tmp_path.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import cli
from cli_runner import run_batch_analysis_from_spec_file
from run_spec import build_batch_manifest, build_run_spec


REPO_ROOT = Path(__file__).resolve().parents[1]
SINGLE_ROUTE_CSV = REPO_ROOT / "data" / "test_data_single_route.csv"

def _silent(_: str) -> None:
    pass


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def shared_data_dir(tmp_path_factory):
    """Two copies of the single-route CSV with distinct stems, created once."""
    data = tmp_path_factory.mktemp("batch_data")
    shutil.copy2(SINGLE_ROUTE_CSV, data / "segment_a.csv")
    shutil.copy2(SINGLE_ROUTE_CSV, data / "segment_b.csv")
    return data


@pytest.fixture(scope="module")
def template_spec_path(tmp_path_factory, shared_data_dir):
    """Template run spec written exactly as the dialog builds it."""
    tmp = tmp_path_factory.mktemp("batch_spec")
    spec = build_run_spec(
        data_file_path=str(SINGLE_ROUTE_CSV),
        x_column="milepoint",
        y_column="structural_strength_ind",
        gap_threshold=0.5,
        method_key="aashto_cda",
        method_parameters={},
        output_json_path=str(tmp / "placeholder.json"),
        application_version="test",
    )
    path = tmp / "template.batch_template.run_spec.json"
    path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Runner API tests
# ---------------------------------------------------------------------------

@pytest.mark.file_io
def test_run_batch_produces_per_file_result_jsons(tmp_path, shared_data_dir, template_spec_path):
    out = tmp_path / "out"
    run_batch_analysis_from_spec_file(
        template_spec_path, shared_data_dir, out, log_callback=_silent
    )
    assert (out / "segment_a.json").exists()
    assert (out / "segment_b.json").exists()


@pytest.mark.file_io
def test_run_batch_summary_counts_two_successes(tmp_path, shared_data_dir, template_spec_path):
    out = tmp_path / "out"
    summary_path = run_batch_analysis_from_spec_file(
        template_spec_path, shared_data_dir, out, log_callback=_silent
    )
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    assert summary["total_files"] == 2
    assert summary["completed"] == 2
    assert summary["failed"] == 0
    assert all(r["status"] == "success" for r in summary["results"])


@pytest.mark.file_io
def test_run_batch_per_file_json_has_standard_analysis_structure(
    tmp_path, shared_data_dir, template_spec_path
):
    out = tmp_path / "out"
    run_batch_analysis_from_spec_file(
        template_spec_path, shared_data_dir, out, log_callback=_silent
    )
    data = json.loads((out / "segment_a.json").read_text(encoding="utf-8"))
    assert "analysis_metadata" in data
    assert "input_parameters" in data
    assert "route_results" in data


@pytest.mark.file_io
def test_run_batch_summary_references_correct_input_files(
    tmp_path, shared_data_dir, template_spec_path
):
    out = tmp_path / "out"
    summary_path = run_batch_analysis_from_spec_file(
        template_spec_path, shared_data_dir, out, log_callback=_silent
    )
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    input_names = {Path(r["input_file"]).name for r in summary["results"]}
    assert input_names == {"segment_a.csv", "segment_b.csv"}


# ---------------------------------------------------------------------------
# CLI entrypoint tests
# ---------------------------------------------------------------------------

@pytest.mark.file_io
def test_cli_run_batch_returns_0_and_prints_summary_path(
    tmp_path, shared_data_dir, template_spec_path, capsys
):
    out = tmp_path / "cli_out"
    rc = cli.main([
        "run",
        "--spec", str(template_spec_path),
        "--input-dir", str(shared_data_dir),
        "--output-dir", str(out),
        "--quiet",
    ])
    assert rc == 0
    printed = capsys.readouterr().out.strip()
    assert printed.endswith("batch_summary.json")


@pytest.mark.file_io
def test_cli_run_batch_creates_per_file_outputs(
    tmp_path, shared_data_dir, template_spec_path, capsys
):
    out = tmp_path / "cli_out"
    cli.main([
        "run",
        "--spec", str(template_spec_path),
        "--input-dir", str(shared_data_dir),
        "--output-dir", str(out),
        "--quiet",
    ])
    assert (out / "segment_a.json").exists()
    assert (out / "segment_b.json").exists()


# ---------------------------------------------------------------------------
# Dialog artifact contract test
# ---------------------------------------------------------------------------

@pytest.mark.file_io
def test_dialog_artifacts_are_consumable_by_cli(tmp_path, shared_data_dir, capsys):
    """Build exactly what the dialog writes, then drive the CLI from the manifest."""
    out = tmp_path / "out"

    # Step 1: build and write the template run spec (mirrors CLIExportDialog._write_batch_artifacts)
    spec = build_run_spec(
        data_file_path=str(SINGLE_ROUTE_CSV),
        x_column="milepoint",
        y_column="structural_strength_ind",
        gap_threshold=0.5,
        method_key="aashto_cda",
        method_parameters={},
        output_json_path=str(tmp_path / "placeholder.json"),
        application_version="test",
    )
    template_spec_path = tmp_path / "export.batch_template.run_spec.json"
    template_spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")

    # Step 2: write the batch manifest (mirrors CLIExportDialog._write_batch_artifacts)
    manifest = build_batch_manifest(
        run_spec_path=str(template_spec_path),
        input_dir=str(shared_data_dir),
        glob="*.csv",
        recurse=False,
        output_dir=str(out),
        summary_json=str(out / "batch_summary.json"),
    )
    manifest_path = tmp_path / "export.batch_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Step 3: user reads the manifest and drives the CLI from its fields
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    rc = cli.main([
        "run",
        "--spec", m["run_spec_path"],
        "--input-dir", m["input_dir"],
        "--output-dir", m["output_dir"],
        "--glob", m["glob"],
        "--quiet",
    ])

    assert rc == 0
    assert (out / "segment_a.json").exists()
    assert (out / "segment_b.json").exists()
    summary = json.loads((out / "batch_summary.json").read_text(encoding="utf-8"))
    assert summary["completed"] == 2
