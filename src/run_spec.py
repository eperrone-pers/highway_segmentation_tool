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


def default_output_json_path(custom_save_name: str) -> Path:
    """Return a reasonable default output json path when the GUI has none."""
    name = (custom_save_name or "highway_segmentation").strip()
    if not name.lower().endswith(".json"):
        name = name + ".json"
    return Path("Results") / name


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
    method_key: str,
    method_parameters: Dict[str, Any],
    output_json_path: str,
    route_column: Optional[str] = None,
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
            "selected_routes": selected_routes,
            "must_break_columns": must_break_columns,
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
