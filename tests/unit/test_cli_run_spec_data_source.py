"""Unit tests for CLI run-spec parsing of the data_source block.

Tests load_and_resolve_run_spec() with database inputs — no live DB needed
since parsing terminates before any connection attempt.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cli_runner import load_and_resolve_run_spec, RunSpecError
from data_sources.base import DataSourceConfig


_COMMON = {
    "spec_version": "1.0.0",
    "method": {"method_key": "aashto_cda", "method_parameters": {}},
    "output": {"output_json_path": "results/out.json", "overwrite": True},
}


def _write_spec(tmp_path: Path, input_block: dict) -> Path:
    spec = {**_COMMON, "input": input_block}
    p = tmp_path / "run_spec.json"
    p.write_text(json.dumps(spec), encoding="utf-8")
    return p


# ------------------------------------------------------------------ #
# Parsing data_source block                                            #
# ------------------------------------------------------------------ #

class TestLoadAndResolveRunSpecDataSource:

    @pytest.mark.unit
    def test_parses_data_source_block(self, tmp_path):
        spec_path = _write_spec(tmp_path, {
            "data_source": {
                "driver": "postgresql",
                "host": "db.example.com",
                "port": 5432,
                "database": "pavement",
                "schema": "public",
                "table_or_view": "iri_survey",
                "username": "analyst",
            },
            "x_column": "MILEPOINT",
            "y_column": "IRI",
            "gap_threshold": 0.1,
        })
        resolved = load_and_resolve_run_spec(spec_path, validate=False)

        assert resolved.data_file_path is None
        assert resolved.data_source_config is not None
        assert isinstance(resolved.data_source_config, DataSourceConfig)

    @pytest.mark.unit
    def test_data_source_config_fields_populated(self, tmp_path):
        spec_path = _write_spec(tmp_path, {
            "data_source": {
                "driver": "oracle",
                "host": "ora.agency.gov",
                "port": 1521,
                "database": "pavement",
                "schema": "dot",
                "table_or_view": "pci_survey",
                "username": "road_eng",
                "connection_name": "Agency Oracle",
            },
            "x_column": "STATION",
            "y_column": "PCI",
            "gap_threshold": 0.25,
        })
        resolved = load_and_resolve_run_spec(spec_path, validate=False)
        cfg = resolved.data_source_config

        assert cfg.source_type == "database"
        assert cfg.driver_key == "oracle"
        assert cfg.host == "ora.agency.gov"
        assert cfg.port == 1521
        assert cfg.database == "pavement"
        assert cfg.schema == "dot"
        assert cfg.table_or_view == "pci_survey"
        assert cfg.username == "road_eng"
        assert cfg.connection_name == "Agency Oracle"

    @pytest.mark.unit
    def test_data_source_partial_fields_allowed(self, tmp_path):
        """SQLite-style spec with only driver + database + table."""
        spec_path = _write_spec(tmp_path, {
            "data_source": {
                "driver": "sqlite",
                "database": "/tmp/test.db",
                "table_or_view": "pavement",
            },
            "x_column": "X",
            "y_column": "Y",
            "gap_threshold": 0.5,
        })
        resolved = load_and_resolve_run_spec(spec_path, validate=False)
        cfg = resolved.data_source_config

        assert cfg.driver_key == "sqlite"
        assert cfg.database == "/tmp/test.db"
        assert cfg.host is None
        assert cfg.username is None

    @pytest.mark.unit
    def test_data_source_missing_driver_raises(self, tmp_path):
        spec_path = _write_spec(tmp_path, {
            "data_source": {
                # "driver" intentionally omitted
                "table_or_view": "iri_survey",
            },
            "x_column": "X",
            "y_column": "Y",
            "gap_threshold": 0.5,
        })
        with pytest.raises(RunSpecError, match="missing required field"):
            load_and_resolve_run_spec(spec_path, validate=False)

    @pytest.mark.unit
    def test_data_source_missing_table_raises(self, tmp_path):
        spec_path = _write_spec(tmp_path, {
            "data_source": {
                "driver": "postgresql",
                # "table_or_view" intentionally omitted
            },
            "x_column": "X",
            "y_column": "Y",
            "gap_threshold": 0.5,
        })
        with pytest.raises(RunSpecError, match="missing required field"):
            load_and_resolve_run_spec(spec_path, validate=False)

    @pytest.mark.unit
    def test_neither_data_file_nor_data_source_raises(self, tmp_path):
        spec_path = _write_spec(tmp_path, {
            "x_column": "X",
            "y_column": "Y",
            "gap_threshold": 0.5,
        })
        with pytest.raises(RunSpecError, match="data_file_path.*data_source|data_source.*data_file_path"):
            load_and_resolve_run_spec(spec_path, validate=False)

    # ------------------------------------------------------------------ #
    # Backward compatibility — data_file_path still works                 #
    # ------------------------------------------------------------------ #

    @pytest.mark.unit
    def test_data_file_path_backward_compat(self, tmp_path):
        csv = tmp_path / "data.csv"
        csv.write_text("x,y\n0.0,85.0\n0.1,90.0\n")
        spec_path = _write_spec(tmp_path, {
            "data_file_path": str(csv),
            "x_column": "x",
            "y_column": "y",
            "gap_threshold": 0.5,
        })
        resolved = load_and_resolve_run_spec(spec_path, validate=False)

        assert resolved.data_file_path == csv
        assert resolved.data_source_config is None

    @pytest.mark.unit
    def test_data_file_path_gives_absolute_path(self, tmp_path):
        csv = tmp_path / "data.csv"
        csv.write_text("x,y\n0.0,85.0\n")
        spec = {
            **_COMMON,
            "input": {
                "data_file_path": "data.csv",   # relative path
                "x_column": "x",
                "y_column": "y",
                "gap_threshold": 0.5,
            },
        }
        spec_path = tmp_path / "run_spec.json"
        spec_path.write_text(json.dumps(spec))
        resolved = load_and_resolve_run_spec(spec_path, validate=False)

        assert resolved.data_file_path.is_absolute()
        assert resolved.data_file_path.name == "data.csv"
