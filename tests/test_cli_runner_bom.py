from __future__ import annotations

import json
from pathlib import Path

import pytest

from cli_runner import load_and_resolve_run_spec


@pytest.mark.file_io
def test_load_run_spec_accepts_utf8_bom(tmp_path: Path) -> None:
    # Write a minimal valid run spec with a UTF-8 BOM (utf-8-sig)
    spec = {
        "spec_version": "1.0.0",
        "input": {
            "data_file_path": "data/test_data_single_route.csv",
            "x_column": "milepoint",
            "y_column": "structural_strength_ind",
            "gap_threshold": 0.5,
        },
        "method": {"method_key": "aashto_cda", "method_parameters": {}},
        "output": {"output_json_path": str(tmp_path / "out.json"), "overwrite": True},
    }

    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8-sig")

    resolved = load_and_resolve_run_spec(spec_path, validate=True)
    assert resolved.method_key == "aashto_cda"
