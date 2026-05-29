"""Unit tests for CLIExportDialog.

These tests instantiate the dialog against a real (withdrawn) Tk root but
never call show() — they exercise the StringVar defaults, the command
preview logic, validation, and artifact writing without blocking on user
input.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import tkinter as tk

from cli_export_dialog import CLIExportDialog


pytestmark = pytest.mark.ui


def _slash(path: str) -> str:
    """Normalize path separators for stable assertions across OSes."""
    return path.replace("\\", "/")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def base_state():
    return {
        "data_file_path": "/data/my_roads.csv",
        "x_column": "milepoint",
        "y_column": "iri",
        "gap_threshold": 0.5,
        "method_key": "aashto_cda",
        "method_parameters": {},
        "route_column": None,
        "selected_routes": None,
        "must_break_columns": None,
        "secondary_break_columns": None,
        "output_json_path": "Results/my_roads.json",
        "app_version": "test",
    }


@pytest.fixture
def dialog(tk_root, base_state):
    dlg = CLIExportDialog(tk_root, state=base_state)
    yield dlg
    try:
        dlg._dialog.destroy()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Default population from state
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_spec_path_default_derives_from_output_json(dialog):
    assert _slash(dialog._spec_path_var.get()) == "Results/my_roads.run_spec.json"


@pytest.mark.unit
def test_input_file_default_matches_state(dialog, base_state):
    assert dialog._input_file_var.get() == base_state["data_file_path"]


@pytest.mark.unit
def test_output_json_default_matches_state(dialog, base_state):
    assert dialog._output_json_var.get() == base_state["output_json_path"]


@pytest.mark.unit
def test_mode_defaults_to_single_file(dialog):
    assert dialog._mode_var.get() == "single"


# ---------------------------------------------------------------------------
# Command preview
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_preview_contains_spec_path_on_init(dialog):
    preview = dialog.get_preview_text()
    assert "run" in preview
    assert "Results/my_roads.run_spec.json" in _slash(preview)


@pytest.mark.unit
def test_preview_updates_when_spec_path_changes(dialog):
    dialog._spec_path_var.set("Results/other.run_spec.json")
    preview = dialog.get_preview_text()
    assert "Results/other.run_spec.json" in preview


@pytest.mark.unit
def test_preview_is_empty_when_spec_path_cleared(dialog):
    dialog._spec_path_var.set("")
    assert dialog.get_preview_text() == ""


@pytest.mark.unit
def test_preview_does_not_change_when_output_json_changes(dialog):
    original = dialog.get_preview_text()
    dialog._output_json_var.set("Results/something_else.json")
    # Output JSON path is in the spec, not the command — preview unchanged
    assert dialog.get_preview_text() == original


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_validate_passes_with_all_fields_present(dialog):
    dialog._spec_path_var.set("Results/my_roads.run_spec.json")
    dialog._input_file_var.set("/data/my_roads.csv")
    dialog._output_json_var.set("Results/my_roads.json")
    assert dialog._validate() is True


@pytest.mark.unit
def test_validate_fails_when_spec_path_empty(dialog):
    dialog._spec_path_var.set("")
    assert dialog._validate() is False


@pytest.mark.unit
def test_validate_fails_when_input_file_empty(dialog):
    dialog._spec_path_var.set("Results/my_roads.run_spec.json")
    dialog._input_file_var.set("")
    assert dialog._validate() is False


@pytest.mark.unit
def test_validate_fails_when_output_json_empty(dialog):
    dialog._spec_path_var.set("Results/my_roads.run_spec.json")
    dialog._input_file_var.set("/data/my_roads.csv")
    dialog._output_json_var.set("")
    assert dialog._validate() is False


# ---------------------------------------------------------------------------
# Artifact writing
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_write_artifacts_creates_spec_file(tmp_path, tk_root, base_state):
    state = dict(base_state)
    state["output_json_path"] = str(tmp_path / "out.json")

    dlg = CLIExportDialog(tk_root, state=state)
    spec_path = tmp_path / "out.run_spec.json"
    dlg._spec_path_var.set(str(spec_path))
    dlg._output_json_var.set(str(tmp_path / "out.json"))

    artifacts = dlg._write_artifacts()

    try:
        dlg._dialog.destroy()
    except Exception:
        pass

    assert spec_path.exists()
    assert artifacts["spec_path"] == spec_path
    assert f'--spec "{spec_path}"' in artifacts["cmd"]


@pytest.mark.unit
def test_write_artifacts_spec_is_valid_json(tmp_path, tk_root, base_state):
    state = dict(base_state)
    state["output_json_path"] = str(tmp_path / "out.json")

    dlg = CLIExportDialog(tk_root, state=state)
    spec_path = tmp_path / "out.run_spec.json"
    dlg._spec_path_var.set(str(spec_path))
    dlg._output_json_var.set(str(tmp_path / "out.json"))
    dlg._write_artifacts()

    try:
        dlg._dialog.destroy()
    except Exception:
        pass

    data = json.loads(spec_path.read_text(encoding="utf-8"))
    assert data["input"]["x_column"] == "milepoint"
    assert data["method"]["method_key"] == "aashto_cda"


@pytest.mark.unit
def test_write_artifacts_reflects_dialog_input_file_override(tmp_path, tk_root, base_state):
    state = dict(base_state)
    state["output_json_path"] = str(tmp_path / "out.json")

    dlg = CLIExportDialog(tk_root, state=state)
    dlg._spec_path_var.set(str(tmp_path / "out.run_spec.json"))
    dlg._input_file_var.set("/data/override.csv")
    dlg._output_json_var.set(str(tmp_path / "out.json"))
    dlg._write_artifacts()

    try:
        dlg._dialog.destroy()
    except Exception:
        pass

    data = json.loads((tmp_path / "out.run_spec.json").read_text(encoding="utf-8"))
    assert data["input"]["data_file_path"] == "/data/override.csv"


@pytest.mark.unit
def test_write_artifacts_calls_log_callback(tmp_path, tk_root, base_state):
    state = dict(base_state)
    state["output_json_path"] = str(tmp_path / "out.json")
    log_messages = []

    dlg = CLIExportDialog(tk_root, state=state, log_callback=log_messages.append)
    dlg._spec_path_var.set(str(tmp_path / "out.run_spec.json"))
    dlg._output_json_var.set(str(tmp_path / "out.json"))
    dlg._write_artifacts()

    try:
        dlg._dialog.destroy()
    except Exception:
        pass

    assert any("Run spec written" in m for m in log_messages)


# ===========================================================================
# Batch mode — defaults
# ===========================================================================

@pytest.mark.unit
def test_batch_input_dir_default_is_empty(dialog):
    assert dialog._batch_input_dir_var.get() == ""


@pytest.mark.unit
def test_batch_glob_default_is_csv(dialog):
    assert dialog._batch_glob_var.get() == "*.csv"


@pytest.mark.unit
def test_batch_recurse_default_is_false(dialog):
    assert dialog._batch_recurse_var.get() is False


@pytest.mark.unit
def test_batch_export_excel_default_is_false(dialog):
    assert dialog._batch_export_excel_var.get() is False


@pytest.mark.unit
def test_batch_continue_on_error_default_is_true(dialog):
    assert dialog._batch_continue_on_error_var.get() is True


@pytest.mark.unit
def test_batch_output_dir_default_derives_from_state(dialog):
    assert _slash(dialog._batch_output_dir_var.get()) == "Results/my_roads_batch"


@pytest.mark.unit
def test_batch_manifest_default_derives_from_state(dialog):
    assert _slash(dialog._batch_manifest_var.get()) == "Results/my_roads.batch_manifest.json"


@pytest.mark.unit
def test_batch_summary_default_derives_from_output_dir(dialog):
    assert _slash(dialog._batch_summary_var.get()) == "Results/my_roads_batch/batch_summary.json"


# ===========================================================================
# Batch mode — command preview
# ===========================================================================

@pytest.mark.unit
def test_preview_empty_in_batch_mode_when_input_dir_missing(dialog):
    dialog._mode_var.set("batch")
    dialog._batch_input_dir_var.set("")
    assert dialog.get_preview_text() == ""


@pytest.mark.unit
def test_preview_shows_run_when_fields_populated(dialog):
    dialog._mode_var.set("batch")
    dialog._batch_input_dir_var.set("/data/incoming")
    dialog._batch_output_dir_var.set("Results/batch_out")
    preview = dialog.get_preview_text()
    assert "run" in preview
    assert "run-batch" not in preview
    assert "--input-dir" in preview
    assert "--output-dir" in preview


@pytest.mark.unit
def test_preview_includes_recurse_flag_when_set(dialog):
    dialog._mode_var.set("batch")
    dialog._batch_input_dir_var.set("/data/incoming")
    dialog._batch_output_dir_var.set("Results/batch_out")
    dialog._batch_recurse_var.set(True)
    assert "--recurse" in dialog.get_preview_text()


@pytest.mark.unit
def test_preview_includes_export_excel_flag_when_set(dialog):
    dialog._mode_var.set("batch")
    dialog._batch_input_dir_var.set("/data/incoming")
    dialog._batch_output_dir_var.set("Results/batch_out")
    dialog._batch_export_excel_var.set(True)
    assert "--export-excel" in dialog.get_preview_text()


# ===========================================================================
# Batch mode — validation
# ===========================================================================

@pytest.mark.unit
def test_batch_validate_fails_when_input_dir_empty(dialog):
    dialog._mode_var.set("batch")
    dialog._batch_input_dir_var.set("")
    assert dialog._validate() is False


@pytest.mark.unit
def test_batch_validate_fails_when_input_dir_does_not_exist(dialog, tmp_path):
    dialog._mode_var.set("batch")
    dialog._batch_input_dir_var.set(str(tmp_path / "nonexistent"))
    assert dialog._validate() is False


@pytest.mark.unit
def test_batch_validate_fails_when_output_dir_empty(dialog, tmp_path):
    dialog._mode_var.set("batch")
    dialog._batch_input_dir_var.set(str(tmp_path))
    dialog._batch_output_dir_var.set("")
    assert dialog._validate() is False


@pytest.mark.unit
def test_batch_validate_fails_on_stem_collision(dialog, tmp_path):
    # Create two CSV files with the same stem in different subdirectories
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "route.csv").write_text("x,y\n1,2")
    (tmp_path / "b" / "route.csv").write_text("x,y\n3,4")

    dialog._mode_var.set("batch")
    dialog._batch_input_dir_var.set(str(tmp_path))
    dialog._batch_recurse_var.set(True)
    dialog._batch_output_dir_var.set(str(tmp_path / "out"))
    assert dialog._validate() is False


@pytest.mark.unit
def test_batch_validate_passes_with_valid_dir_and_files(dialog, tmp_path):
    (tmp_path / "a.csv").write_text("x,y\n1,2")
    (tmp_path / "b.csv").write_text("x,y\n3,4")

    dialog._mode_var.set("batch")
    dialog._batch_input_dir_var.set(str(tmp_path))
    dialog._batch_output_dir_var.set(str(tmp_path / "out"))
    assert dialog._validate() is True


# ===========================================================================
# Batch mode — preflight
# ===========================================================================

@pytest.mark.unit
def test_preflight_shows_matched_file_count(dialog, tmp_path):
    (tmp_path / "a.csv").write_text("x,y")
    (tmp_path / "b.csv").write_text("x,y")
    dialog._batch_input_dir_var.set(str(tmp_path))
    assert "2" in dialog._preflight_matched_var.get()


@pytest.mark.unit
def test_preflight_no_collision_message_when_stems_unique(dialog, tmp_path):
    (tmp_path / "alpha.csv").write_text("x,y")
    (tmp_path / "beta.csv").write_text("x,y")
    dialog._batch_input_dir_var.set(str(tmp_path))
    assert "No naming collisions" in dialog._preflight_warnings_var.get()


@pytest.mark.unit
def test_preflight_warns_on_duplicate_stems(dialog, tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "route.csv").write_text("x,y")
    (tmp_path / "sub" / "route.csv").write_text("x,y")
    dialog._batch_input_dir_var.set(str(tmp_path))
    dialog._batch_recurse_var.set(True)
    assert "WARNING" in dialog._preflight_warnings_var.get()


# ===========================================================================
# Batch mode — artifact writing
# ===========================================================================

@pytest.mark.unit
def test_write_artifacts_batch_creates_spec_and_manifest(tmp_path, tk_root, base_state):
    state = dict(base_state)
    state["output_json_path"] = str(tmp_path / "out.json")

    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "r1.csv").write_text("x,y\n1,2")

    dlg = CLIExportDialog(tk_root, state=state)
    dlg._mode_var.set("batch")
    dlg._spec_path_var.set(str(tmp_path / "out.batch_template.run_spec.json"))
    dlg._batch_input_dir_var.set(str(tmp_path / "data"))
    dlg._batch_output_dir_var.set(str(tmp_path / "out_batch"))
    dlg._batch_manifest_var.set(str(tmp_path / "out.batch_manifest.json"))
    dlg._batch_summary_var.set(str(tmp_path / "out_batch" / "batch_summary.json"))

    artifacts = dlg._write_artifacts()

    try:
        dlg._dialog.destroy()
    except Exception:
        pass

    assert artifacts["mode"] == "batch"
    assert Path(artifacts["spec_path"]).exists()
    assert Path(artifacts["manifest_path"]).exists()
    assert "run" in artifacts["cmd"]
    assert "run-batch" not in artifacts["cmd"]


@pytest.mark.unit
def test_write_artifacts_batch_manifest_has_correct_fields(tmp_path, tk_root, base_state):
    state = dict(base_state)
    state["output_json_path"] = str(tmp_path / "out.json")

    (tmp_path / "data").mkdir()

    dlg = CLIExportDialog(tk_root, state=state)
    dlg._mode_var.set("batch")
    dlg._spec_path_var.set(str(tmp_path / "out.batch_template.run_spec.json"))
    dlg._batch_input_dir_var.set(str(tmp_path / "data"))
    dlg._batch_output_dir_var.set(str(tmp_path / "out_batch"))
    dlg._batch_manifest_var.set(str(tmp_path / "out.batch_manifest.json"))
    dlg._batch_summary_var.set(str(tmp_path / "out_batch" / "batch_summary.json"))
    dlg._batch_export_excel_var.set(True)
    dlg._write_artifacts()

    try:
        dlg._dialog.destroy()
    except Exception:
        pass

    manifest = json.loads((tmp_path / "out.batch_manifest.json").read_text())
    assert manifest["manifest_version"] == "1.0.0"
    assert manifest["export_excel"] is True
    assert manifest["continue_on_error"] is True
