from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_regression_template() -> Dict[str, Any]:
    """Load the regression parameters template (source of truth)."""
    template_path = Path(__file__).parent / "test_parameters_template.json"
    return json.loads(template_path.read_text(encoding="utf-8"))


def get_methods_and_datasets_from_template() -> Tuple[List[str], List[str]]:
    """Derive method and dataset keys from the regression template."""
    template = load_regression_template()

    method_specific = template.get("method_specific", {}) or {}
    methods = ["single", "multi"] + sorted(
        [m for m in method_specific.keys() if isinstance(m, str)]
    )

    # de-dupe but preserve order
    seen = set()
    methods = [m for m in methods if not (m in seen or seen.add(m))]

    data_confs = template.get("data_configurations", {}) or {}
    datasets = sorted([k for k in data_confs.keys() if isinstance(k, str)])
    return methods, datasets


def get_dataset_config(dataset_key: str) -> Dict[str, Any]:
    template = load_regression_template()
    data_confs = template.get("data_configurations", {}) or {}
    if dataset_key not in data_confs:
        raise KeyError(f"Dataset key not found in regression template: {dataset_key}")
    return data_confs[dataset_key]


def get_result_filename(method_key: str, dataset: str, extension: str, *, prefix: str = "regression") -> str:
    return f"{prefix}_{method_key}_{dataset}.{extension}"
