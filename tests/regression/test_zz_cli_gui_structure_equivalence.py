from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pytest

from tests.regression.regression_matrix import (
    get_methods_and_datasets_from_template,
    get_result_filename,
)

METHODS_TO_TEST, DATASETS_TO_TEST = get_methods_and_datasets_from_template()


def _type_tag(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    # Fallback for unexpected JSON types
    return type(value).__name__


Shape = Any


def _merge_shapes(shapes: Iterable[Shape]) -> Shape:
    shapes = list(shapes)
    if not shapes:
        return {"__type__": "unknown"}

    # If all identical, keep it simple.
    first = shapes[0]
    if all(s == first for s in shapes):
        return first

    # Merge unions of scalar type-tags.
    if all(isinstance(s, str) for s in shapes):
        return {"__union__": sorted(set(shapes))}

    # Merge list/item shapes.
    if all(isinstance(s, dict) and s.get("__type__") == "array" for s in shapes):
        return {
            "__type__": "array",
            "items": _merge_shapes([s.get("items") for s in shapes]),
        }

    # Merge object shapes by key.
    if all(isinstance(s, dict) and s.get("__type__") == "object" for s in shapes):
        merged_keys: Dict[str, Shape] = {}
        all_keys = set()
        for s in shapes:
            all_keys.update((s.get("keys") or {}).keys())

        for key in sorted(all_keys):
            merged_keys[key] = _merge_shapes(
                [
                    (s.get("keys") or {}).get(key, "__missing__")
                    for s in shapes
                ]
            )

        return {"__type__": "object", "keys": merged_keys}

    # Mixed/unexpected shapes: represent as a union.
    return {"__union__": sorted({_stable_repr(s) for s in shapes})}


def _stable_repr(shape: Shape) -> str:
    # Deterministic string representation for union/debug.
    try:
        return json.dumps(shape, sort_keys=True)
    except TypeError:
        return repr(shape)


def _shape(value: Any) -> Shape:
    t = _type_tag(value)

    if t == "object":
        assert isinstance(value, dict)
        return {
            "__type__": "object",
            "keys": {k: _shape(v) for k, v in sorted(value.items(), key=lambda kv: kv[0])},
        }

    if t == "array":
        assert isinstance(value, list)
        # Merge over all items so variable-length outputs still share a stable shape.
        return {"__type__": "array", "items": _merge_shapes([_shape(v) for v in value])}

    # Scalars collapse to a type tag.
    return t


def _first_mismatch_path(a: Shape, b: Shape, path: str = "$") -> Tuple[str, Shape, Shape] | None:
    if a == b:
        return None

    # Recurse into object shapes
    if (
        isinstance(a, dict)
        and isinstance(b, dict)
        and a.get("__type__") == "object"
        and b.get("__type__") == "object"
    ):
        a_keys = a.get("keys") or {}
        b_keys = b.get("keys") or {}
        for key in sorted(set(a_keys.keys()) | set(b_keys.keys())):
            res = _first_mismatch_path(a_keys.get(key, "__missing__"), b_keys.get(key, "__missing__"), f"{path}.{key}")
            if res is not None:
                return res
        return (path, a, b)

    # Recurse into array shapes
    if (
        isinstance(a, dict)
        and isinstance(b, dict)
        and a.get("__type__") == "array"
        and b.get("__type__") == "array"
    ):
        return _first_mismatch_path(a.get("items"), b.get("items"), f"{path}[*]")

    return (path, a, b)


@pytest.mark.file_io
def test_cli_vs_gui_results_have_same_structure() -> None:
    """Ensure CLI and GUI regression outputs have the same JSON *structure*.

    This test intentionally ignores *values* (timestamps, runtime, stochastic GA
    results, counts), and compares only the nested key/type layout.
    """
    outputs_json_dir = Path(__file__).parent / "outputs" / "json"

    found_pairs = 0
    missing: List[str] = []
    mismatches: List[str] = []

    for method_key in METHODS_TO_TEST:
        for dataset in DATASETS_TO_TEST:
            gui_name = get_result_filename(method_key, dataset, "json")
            cli_name = f"cli_{gui_name}"

            gui_path = outputs_json_dir / gui_name
            cli_path = outputs_json_dir / cli_name

            if not gui_path.exists() or not cli_path.exists():
                missing.append(f"{gui_name} / {cli_name}")
                continue

            found_pairs += 1

            gui_data = json.loads(gui_path.read_text(encoding="utf-8"))
            cli_data = json.loads(cli_path.read_text(encoding="utf-8"))

            gui_shape = _shape(gui_data)
            cli_shape = _shape(cli_data)

            if gui_shape != cli_shape:
                mismatch = _first_mismatch_path(gui_shape, cli_shape)
                if mismatch is None:
                    mismatches.append(f"{gui_name}: structure differs")
                else:
                    p, a, b = mismatch
                    mismatches.append(
                        f"{gui_name}: first mismatch at {p}\n"
                        f"  gui={_stable_repr(a)}\n"
                        f"  cli={_stable_repr(b)}"
                    )

    if found_pairs == 0:
        pytest.skip(
            "No GUI/CLI regression output pairs found under tests/regression/outputs/json. "
            "Run the regression suites (tests/regression/test_complete_workflow_regression.py and "
            "tests/regression/test_cli_workflow_regression.py) to generate artifacts first."
        )

    if missing:
        pytest.fail(
            "Some expected GUI/CLI regression output pairs are missing under tests/regression/outputs/json:\n- "
            + "\n- ".join(sorted(missing))
        )

    if mismatches:
        pytest.fail("CLI vs GUI JSON structure mismatch(es):\n\n" + "\n\n".join(mismatches))
