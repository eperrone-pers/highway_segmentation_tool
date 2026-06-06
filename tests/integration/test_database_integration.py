"""Integration tests for DatabaseDataSource using a real SQLite database.

SQLite is built into Python's standard library so these tests require no
additional packages and run in CI without any external services.  They
exercise the full SQLAlchemy path — engine creation, query execution, and
DataFrame extraction — that unit tests mock out.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import sqlalchemy

from data_sources.base import DataSourceConfig, DataSourceError
from data_sources.database_source import DatabaseDataSource


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def sqlite_db(tmp_path):
    """Create a minimal SQLite database with pavement test data.

    Returns the path to the .db file.
    """
    db_path = tmp_path / "pavement.db"
    engine = sqlalchemy.create_engine(f"sqlite:///{db_path}")

    with engine.connect() as conn:
        conn.execute(sqlalchemy.text("""
            CREATE TABLE iri_survey (
                milepoint REAL,
                iri        REAL,
                route      TEXT,
                surface    TEXT
            )
        """))
        conn.execute(sqlalchemy.text("""
            INSERT INTO iri_survey VALUES
                (0.0, 85.0, 'US101', 'AC'),
                (0.1, 90.2, 'US101', 'AC'),
                (0.2, 78.5, 'US101', 'PCC'),
                (0.3, 82.1, 'US101', 'PCC'),
                (0.4, 88.0, 'US101', 'AC'),
                (0.0, 102.1, 'I5', 'AC'),
                (0.1, 99.8, 'I5', 'AC'),
                (0.2, 95.3, 'I5', 'AC')
        """))
        conn.commit()

    return db_path


@pytest.fixture
def sqlite_config(sqlite_db):
    return DataSourceConfig(
        source_type="database",
        driver_key="sqlite",
        database=str(sqlite_db),
        table_or_view="iri_survey",
    )


# ------------------------------------------------------------------ #
# DatabaseDataSource — SQLite live tests                               #
# ------------------------------------------------------------------ #

class TestDatabaseDataSourceSQLite:

    def test_get_available_columns(self, sqlite_config):
        src = DatabaseDataSource(sqlite_config)
        cols = src.get_available_columns()
        assert set(cols) == {"milepoint", "iri", "route", "surface"}

    def test_load_data_returns_all_columns_as_strings(self, sqlite_config):
        src = DatabaseDataSource(sqlite_config)
        df = src.load_data(x_col="milepoint", y_col="iri")
        assert set(df.columns) >= {"milepoint", "iri", "route", "surface"}
        for col in df.columns:
            assert pd.api.types.is_string_dtype(df[col]), (
                f"Column '{col}' should be string dtype"
            )

    def test_load_data_returns_all_rows(self, sqlite_config):
        src = DatabaseDataSource(sqlite_config)
        df = src.load_data(x_col="milepoint", y_col="iri")
        assert len(df) == 8

    def test_load_data_filters_by_selected_routes(self, sqlite_config):
        src = DatabaseDataSource(sqlite_config)
        df = src.load_data(
            x_col="milepoint", y_col="iri",
            route_col="route", selected_routes=["US101"],
        )
        assert len(df) == 5
        assert set(df["route"].unique()) == {"US101"}

    def test_load_data_raises_for_missing_x_column(self, sqlite_config):
        src = DatabaseDataSource(sqlite_config)
        with pytest.raises(DataSourceError, match="Required column 'nonexistent'"):
            src.load_data(x_col="nonexistent", y_col="iri")

    def test_get_available_schemas(self, sqlite_config):
        src = DatabaseDataSource(sqlite_config)
        schemas = src.get_available_schemas()
        assert isinstance(schemas, list)

    def test_get_available_tables_and_views(self, sqlite_config):
        src = DatabaseDataSource(sqlite_config)
        items = src.get_available_tables_and_views()
        names = [name for name, _ in items]
        assert "iri_survey" in names

    def test_detect_routes(self, sqlite_config):
        src = DatabaseDataSource(sqlite_config)
        routes = src.detect_routes("route")
        assert sorted(routes) == ["I5", "US101"]

    def test_get_row_count(self, sqlite_config):
        src = DatabaseDataSource(sqlite_config)
        count = src.get_row_count()
        assert count == 8

    def test_get_traceability_info_no_credentials(self, sqlite_config):
        src = DatabaseDataSource(sqlite_config)
        info = src.get_traceability_info()
        assert info["source_type"] == "database"
        assert info["driver"] == "sqlite"
        assert info["table_or_view"] == "iri_survey"
        assert "password" not in info


# ------------------------------------------------------------------ #
# End-to-end CLI run with SQLite via data_source block                 #
# ------------------------------------------------------------------ #

@pytest.mark.file_io
def test_cli_run_with_sqlite_data_source(tmp_path, sqlite_db):
    """Full pipeline: CLI run-spec with data_source block → results JSON."""
    from cli_runner import run_analysis_from_spec_file

    spec = {
        "spec_version": "1.0.0",
        "input": {
            "data_source": {
                "driver": "sqlite",
                "database": str(sqlite_db),
                "table_or_view": "iri_survey",
            },
            "x_column": "milepoint",
            "y_column": "iri",
            "route_column": "route",
            "gap_threshold": 0.5,
        },
        "method": {
            "method_key": "aashto_cda",
            "method_parameters": {},
        },
        "output": {
            "output_json_path": str(tmp_path / "results.json"),
            "overwrite": True,
        },
    }
    spec_path = tmp_path / "run_spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    output_path = run_analysis_from_spec_file(
        spec_path, validate_spec=False, log_callback=lambda _: None
    )
    out = Path(output_path)

    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))

    assert "analysis_metadata" in data
    assert "route_results" in data
    assert len(data["route_results"]) > 0

    # Traceability: source_type must be "database", never "file"
    input_info = data["analysis_metadata"]["input_file_info"]
    assert input_info["source_type"] == "database"
    assert input_info["driver"] == "sqlite"
    assert input_info["table_or_view"] == "iri_survey"
    assert "password" not in str(input_info)


@pytest.mark.file_io
def test_cli_run_sqlite_single_route_mode(tmp_path, sqlite_db):
    """No route_column — treats the full table as a single route."""
    from cli_runner import run_analysis_from_spec_file

    spec = {
        "spec_version": "1.0.0",
        "input": {
            "data_source": {
                "driver": "sqlite",
                "database": str(sqlite_db),
                "table_or_view": "iri_survey",
            },
            "x_column": "milepoint",
            "y_column": "iri",
            "gap_threshold": 0.5,
        },
        "method": {"method_key": "aashto_cda", "method_parameters": {}},
        "output": {
            "output_json_path": str(tmp_path / "results.json"),
            "overwrite": True,
        },
    }
    spec_path = tmp_path / "run_spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    output_path = run_analysis_from_spec_file(
        spec_path, validate_spec=False, log_callback=lambda _: None
    )
    data = json.loads(Path(output_path).read_text(encoding="utf-8"))
    assert len(data["route_results"]) == 1
