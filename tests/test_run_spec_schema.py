from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest


_COMMON_TAIL = {
    "method": {"method_key": "aashto_cda", "method_parameters": {}},
    "output": {"output_json_path": "results/out.json"},
}


def _load_schema() -> dict:
    repo_root = Path(__file__).resolve().parents[1]
    return json.loads(
        (repo_root / "src" / "highway_segmentation_run_spec_schema.json").read_text()
    )


def _validate(instance: dict) -> list:
    schema = _load_schema()
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    return sorted(validator.iter_errors(instance), key=lambda e: e.json_path)


def test_run_spec_fixture_validates_against_schema() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    schema_path = repo_root / "src" / "highway_segmentation_run_spec_schema.json"
    fixture_path = repo_root / "tests" / "fixtures" / "run_spec_minimal.json"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    instance = json.loads(fixture_path.read_text(encoding="utf-8"))

    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.json_path)
    assert errors == [], "\n".join([f"{e.json_path}: {e.message}" for e in errors])


def test_run_spec_rejects_unknown_top_level_keys() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    schema_path = repo_root / "src" / "highway_segmentation_run_spec_schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    instance = {
        "spec_version": "1.0.0",
        "input": {
            "data_file_path": "data/test_data_single_route.csv",
            "x_column": "mile",
            "y_column": "value",
            "gap_threshold": 0.5,
        },
        "method": {"method_key": "multi", "method_parameters": {}},
        "output": {"output_json_path": "Results/out.json"},
        "typo_key_should_fail": True,
    }

    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = list(validator.iter_errors(instance))
    assert any("Additional properties" in e.message for e in errors)


# ------------------------------------------------------------------ #
# data_source block — schema validation                               #
# ------------------------------------------------------------------ #

def test_data_source_block_validates() -> None:
    instance = {
        "spec_version": "1.0.0",
        "input": {
            "data_source": {
                "driver": "postgresql",
                "host": "db.example.com",
                "port": 5432,
                "database": "pavement",
                "table_or_view": "iri_survey",
                "username": "analyst",
            },
            "x_column": "MILEPOINT",
            "y_column": "IRI",
            "gap_threshold": 0.1,
        },
        **_COMMON_TAIL,
    }
    errors = _validate(instance)
    assert errors == [], [f"{e.json_path}: {e.message}" for e in errors]


def test_data_source_sqlite_minimal_validates() -> None:
    instance = {
        "spec_version": "1.0.0",
        "input": {
            "data_source": {
                "driver": "sqlite",
                "database": "data/local.db",
                "table_or_view": "pavement_condition",
            },
            "x_column": "STATION",
            "y_column": "PCI",
            "gap_threshold": 0.25,
        },
        **_COMMON_TAIL,
    }
    errors = _validate(instance)
    assert errors == [], [f"{e.json_path}: {e.message}" for e in errors]


def test_data_source_missing_driver_fails() -> None:
    instance = {
        "spec_version": "1.0.0",
        "input": {
            "data_source": {
                # "driver" intentionally omitted
                "table_or_view": "iri_survey",
            },
            "x_column": "MILEPOINT",
            "y_column": "IRI",
            "gap_threshold": 0.1,
        },
        **_COMMON_TAIL,
    }
    errors = _validate(instance)
    assert any("'driver' is a required property" in e.message for e in errors)


def test_data_source_missing_table_or_view_fails() -> None:
    instance = {
        "spec_version": "1.0.0",
        "input": {
            "data_source": {
                "driver": "postgresql",
                "host": "db.example.com",
                # "table_or_view" intentionally omitted
            },
            "x_column": "MILEPOINT",
            "y_column": "IRI",
            "gap_threshold": 0.1,
        },
        **_COMMON_TAIL,
    }
    errors = _validate(instance)
    assert any("'table_or_view' is a required property" in e.message for e in errors)


def test_schema_rejects_both_data_file_and_data_source() -> None:
    """oneOf must reject documents that satisfy both alternatives."""
    instance = {
        "spec_version": "1.0.0",
        "input": {
            "data_file_path": "data/file.csv",
            "data_source": {
                "driver": "postgresql",
                "table_or_view": "iri_survey",
            },
            "x_column": "MILEPOINT",
            "y_column": "IRI",
            "gap_threshold": 0.1,
        },
        **_COMMON_TAIL,
    }
    errors = _validate(instance)
    assert len(errors) > 0, "Schema must reject documents with both data_file_path and data_source"


def test_schema_rejects_neither_data_file_nor_data_source() -> None:
    """oneOf must reject documents that satisfy neither alternative."""
    instance = {
        "spec_version": "1.0.0",
        "input": {
            "x_column": "MILEPOINT",
            "y_column": "IRI",
            "gap_threshold": 0.1,
        },
        **_COMMON_TAIL,
    }
    errors = _validate(instance)
    assert len(errors) > 0, "Schema must reject documents with neither data_file_path nor data_source"


def test_data_file_path_backward_compatible() -> None:
    """Existing data_file_path specs must still validate after schema update."""
    instance = {
        "spec_version": "1.0.0",
        "input": {
            "data_file_path": "data/my_highway_data.csv",
            "x_column": "MILEPOINT",
            "y_column": "IRI",
            "gap_threshold": 0.5,
        },
        **_COMMON_TAIL,
    }
    errors = _validate(instance)
    assert errors == [], [f"{e.json_path}: {e.message}" for e in errors]


def test_data_source_unknown_field_rejected() -> None:
    instance = {
        "spec_version": "1.0.0",
        "input": {
            "data_source": {
                "driver": "postgresql",
                "table_or_view": "iri_survey",
                "typo_field": "should_fail",
            },
            "x_column": "MILEPOINT",
            "y_column": "IRI",
            "gap_threshold": 0.1,
        },
        **_COMMON_TAIL,
    }
    errors = _validate(instance)
    assert any("Additional properties" in e.message for e in errors)
