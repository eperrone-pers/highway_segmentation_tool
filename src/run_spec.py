"""Run-spec helpers shared by GUI and CLI.

The *schema* for run specs is defined in:
- src/highway_segmentation_run_spec_schema.json

This module focuses on building a run-spec dict and picking default paths.
It intentionally avoids importing tkinter.
"""

from __future__ import annotations

import datetime as _dt
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


RUN_SPEC_VERSION = "1.0.0"
RUN_SPEC_SCHEMA_ID = "https://mottmac.com/schemas/highway-segmentation/run-spec/v1.0.0"


def _iso_utc_now() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_run_spec_path_for_output(output_json_path: os.PathLike[str] | str) -> Path:
    out = Path(output_json_path)
    base = out.with_suffix("")
    return base.with_name(base.name + ".run_spec.json")


def build_run_spec(
    *,
    data_file_path: str,
    x_column: str,
    y_column: str,
    gap_threshold: float,
    must_break_columns: Optional[List[str]] = None,
    secondary_break_columns: Optional[List[str]] = None,
    method_key: str,
    method_parameters: Dict[str, Any],
    output_json_path: str,
    route_column: Optional[str] = None,
    direction_column: Optional[str] = None,
    lane_column: Optional[str] = None,
    x_min: Optional[float] = None,
    x_max: Optional[float] = None,
    selected_routes: Optional[List[str]] = None,
    overwrite: bool = True,
    created_at: Optional[str] = None,
    application: str = "Highway Segmentation",
    application_version: str = "dev",
) -> Dict[str, Any]:
    """Build a run spec dict matching the JSON schema.

    Note: `method_parameters` is intentionally flexible (extensible across methods).
    """
    created_at = created_at or _iso_utc_now()

    return {
        "$schema": RUN_SPEC_SCHEMA_ID,
        "spec_version": RUN_SPEC_VERSION,
        "created_at": created_at,
        "software_version": {"application": application, "version": application_version},
        "input": {
            "data_file_path": data_file_path,
            "x_column": x_column,
            "y_column": y_column,
            "gap_threshold": float(gap_threshold),
            "route_column": route_column,
            "direction_column": direction_column,
            "lane_column": lane_column,
            "x_min": x_min,
            "x_max": x_max,
            "selected_routes": selected_routes,
            "must_break_columns": must_break_columns,
            "secondary_break_columns": secondary_break_columns,
        },
        "method": {
            "method_key": method_key,
            "method_parameters": method_parameters or {},
        },
        "output": {
            "output_json_path": output_json_path,
            "overwrite": bool(overwrite),
        },
    }


def default_batch_run_spec_path(output_json_path: os.PathLike[str] | str) -> Path:
    """Return default batch-template run-spec path derived from the output JSON path.

    Example: Results/network_analysis.json -> Results/network_analysis.batch_template.run_spec.json
    """
    out = Path(output_json_path)
    base = out.with_suffix("")
    return base.with_name(base.name + ".batch_template.run_spec.json")


def default_batch_output_dir(output_json_path: os.PathLike[str] | str) -> Path:
    """Return default batch output directory derived from the output JSON path stem.

    Example: Results/network_analysis.json -> Results/network_analysis_batch
    """
    out = Path(output_json_path)
    stem = out.with_suffix("").name
    return out.parent / f"{stem}_batch"


def default_batch_manifest_path(output_json_path: os.PathLike[str] | str) -> Path:
    """Return default batch manifest path adjacent to the output JSON.

    Example: Results/network_analysis.json -> Results/network_analysis.batch_manifest.json
    """
    out = Path(output_json_path)
    base = out.with_suffix("")
    return base.with_name(base.name + ".batch_manifest.json")


def default_batch_summary_path(output_dir: os.PathLike[str] | str) -> Path:
    """Return default batch summary path inside the given output directory."""
    return Path(output_dir) / "batch_summary.json"


def build_batch_manifest(
    *,
    run_spec_path: os.PathLike[str] | str,
    input_dir: os.PathLike[str] | str,
    glob: str,
    recurse: bool,
    output_dir: os.PathLike[str] | str,
    summary_json: os.PathLike[str] | str,
    continue_on_error: bool = True,
    export_excel: bool = False,
    application: str = "Highway Segmentation",
    application_version: str = "dev",
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a batch manifest dict describing how to re-execute a batch run."""
    return {
        "manifest_version": "1.0.0",
        "run_spec_path": str(run_spec_path),
        "input_dir": str(input_dir),
        "glob": glob,
        "recurse": bool(recurse),
        "output_dir": str(output_dir),
        "summary_json": str(summary_json),
        "continue_on_error": bool(continue_on_error),
        "export_excel": bool(export_excel),
        "created_at": created_at or _iso_utc_now(),
        "created_by": {
            "application": application,
            "version": application_version,
        },
    }


def build_command_for_batch_run(
    spec_path: os.PathLike[str] | str,
    input_dir: os.PathLike[str] | str,
    output_dir: os.PathLike[str] | str,
    *,
    glob_pattern: str = "*.csv",
    recurse: bool = False,
    summary_json: Optional[os.PathLike[str] | str] = None,
    continue_on_error: bool = True,
    export_excel: bool = False,
) -> str:
    """Build a copy/paste-friendly CLI command for a batch run.

    Always emits --glob and --summary-json explicitly so the command is self-documenting
    and reproducible even when the values match the CLI defaults.
    """
    resolved_summary = (
        str(summary_json) if summary_json is not None else str(default_batch_summary_path(output_dir))
    )
    parts = [
        "python src/cli.py run",
        f'--spec "{spec_path}"',
        f'--input-dir "{input_dir}"',
        f'--glob "{glob_pattern}"',
        f'--output-dir "{output_dir}"',
        f'--summary-json "{resolved_summary}"',
    ]
    if recurse:
        parts.append("--recurse")
    if not continue_on_error:
        parts.append("--stop-on-error")
    if export_excel:
        parts.append("--export-excel")
    return " ".join(parts)


def build_command_for_run_spec(spec_path: os.PathLike[str] | str) -> str:
    """Build a copy/paste-friendly CLI command to execute a run spec.

    Current policy:
    - Use `python` for simplicity (assumes user's environment is activated).
    - Call the repo CLI module directly: `python src/cli.py run --spec ...`

    This command works on Windows PowerShell/CMD and on macOS/Linux terminals.
    """
    spec_path = str(spec_path)

    # Always quote; Windows paths often contain spaces.
    if sys.platform.startswith("win"):
        return f'python src/cli.py run --spec "{spec_path}"'

    return f'python src/cli.py run --spec "{spec_path}"'
