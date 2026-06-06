"""Unit tests for the data_sources package (Step 1 — abstraction layer)."""

import pytest
import pandas as pd

from data_sources.base import DataSourceConfig, DataSourceError
from data_sources.registry import get_data_source
from data_sources.file_source import FileDataSource
from data_sources.database_source import DatabaseDataSource
from data_sources.driver_registry import DATABASE_DRIVERS, DRIVER_BY_KEY, get_driver


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def csv_file(tmp_path):
    """Minimal CSV with x, y, and route columns."""
    p = tmp_path / "test_data.csv"
    p.write_text(
        "milepoint,iri,route\n"
        "0.0,85.0,US101\n"
        "0.1,90.2,US101\n"
        "0.2,78.5,US101\n"
        "0.0,102.1,I5\n"
        "0.1,99.8,I5\n"
    )
    return p


@pytest.fixture
def file_config(csv_file):
    return DataSourceConfig(source_type="file", file_path=str(csv_file))


# ------------------------------------------------------------------ #
# DataSourceConfig                                                     #
# ------------------------------------------------------------------ #

class TestDataSourceConfig:
    def test_defaults_to_file_source(self):
        config = DataSourceConfig()
        assert config.source_type == "file"

    def test_file_config_fields(self, csv_file):
        config = DataSourceConfig(source_type="file", file_path=str(csv_file))
        assert config.source_type == "file"
        assert config.file_path == str(csv_file)

    def test_database_config_fields(self):
        config = DataSourceConfig(
            source_type="database",
            driver_key="postgresql",
            host="localhost",
            port=5432,
            database="pavement",
            username="analyst",
        )
        assert config.source_type == "database"
        assert config.driver_key == "postgresql"
        assert config.port == 5432


# ------------------------------------------------------------------ #
# FileDataSource                                                       #
# ------------------------------------------------------------------ #

class TestFileDataSource:
    def test_raises_if_no_file_path(self):
        config = DataSourceConfig(source_type="file", file_path=None)
        with pytest.raises(DataSourceError, match="file_path"):
            FileDataSource(config)

    def test_raises_if_file_missing(self, tmp_path):
        config = DataSourceConfig(
            source_type="file", file_path=str(tmp_path / "missing.csv")
        )
        with pytest.raises(DataSourceError, match="not found"):
            FileDataSource(config)

    def test_source_type(self, file_config):
        src = FileDataSource(file_config)
        assert src.source_type == "file"

    def test_display_name_is_filename(self, file_config, csv_file):
        src = FileDataSource(file_config)
        assert src.display_name == csv_file.name

    def test_get_available_columns(self, file_config):
        src = FileDataSource(file_config)
        cols = src.get_available_columns()
        assert cols == ["milepoint", "iri", "route"]

    def test_load_data_returns_dataframe(self, file_config):
        src = FileDataSource(file_config)
        df = src.load_data(x_col="milepoint", y_col="iri")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5

    def test_load_data_all_string_dtype(self, file_config):
        src = FileDataSource(file_config)
        df = src.load_data(x_col="milepoint", y_col="iri")
        for col in df.columns:
            assert pd.api.types.is_string_dtype(df[col]), (
                f"Column '{col}' should be string dtype, got {df[col].dtype}"
            )

    def test_load_data_filter_by_selected_routes(self, file_config):
        src = FileDataSource(file_config)
        df = src.load_data(
            x_col="milepoint", y_col="iri",
            route_col="route", selected_routes=["US101"]
        )
        assert len(df) == 3
        assert df["route"].unique().tolist() == ["US101"]

    def test_load_data_no_filter_returns_all(self, file_config):
        src = FileDataSource(file_config)
        df = src.load_data(x_col="milepoint", y_col="iri", route_col="route")
        assert len(df) == 5

    def test_detect_routes(self, file_config):
        src = FileDataSource(file_config)
        routes = src.detect_routes("route")
        assert routes == ["I5", "US101"]

    def test_detect_routes_sorted(self, tmp_path):
        p = tmp_path / "routes.csv"
        p.write_text("mp,iri,route\n0,80,Z_Route\n1,85,A_Route\n2,90,M_Route\n")
        src = FileDataSource(DataSourceConfig(source_type="file", file_path=str(p)))
        assert src.detect_routes("route") == ["A_Route", "M_Route", "Z_Route"]

    def test_detect_routes_excludes_blank(self, tmp_path):
        p = tmp_path / "blanks.csv"
        p.write_text("mp,iri,route\n0,80,US101\n1,85,\n2,90,US101\n")
        src = FileDataSource(DataSourceConfig(source_type="file", file_path=str(p)))
        routes = src.detect_routes("route")
        assert "" not in routes
        assert "US101" in routes

    def test_get_traceability_info(self, file_config, csv_file):
        src = FileDataSource(file_config)
        info = src.get_traceability_info()
        assert info["source_type"] == "file"
        assert info["data_file_name"] == csv_file.name
        assert info["data_file_path"] == str(csv_file)
        assert isinstance(info["data_file_size_bytes"], int)


# ------------------------------------------------------------------ #
# Registry                                                             #
# ------------------------------------------------------------------ #

class TestRegistry:
    def test_file_source_returns_file_data_source(self, file_config):
        src = get_data_source(file_config)
        assert isinstance(src, FileDataSource)

    def test_database_source_returns_database_data_source(self):
        config = DataSourceConfig(
            source_type="database", driver_key="postgresql"
        )
        src = get_data_source(config)
        assert isinstance(src, DatabaseDataSource)

    def test_unknown_source_type_raises(self):
        config = DataSourceConfig(source_type="ftp")
        with pytest.raises(DataSourceError, match="Unknown source_type"):
            get_data_source(config)


# ------------------------------------------------------------------ #
# Driver registry                                                      #
# ------------------------------------------------------------------ #

class TestDriverRegistry:
    def test_all_drivers_have_required_fields(self):
        required_attrs = [
            "driver_key", "display_name", "fields", "required_packages"
        ]
        for driver in DATABASE_DRIVERS:
            for attr in required_attrs:
                assert hasattr(driver, attr), (
                    f"Driver '{driver.driver_key}' missing attribute '{attr}'"
                )

    def test_driver_keys_are_unique(self):
        keys = [d.driver_key for d in DATABASE_DRIVERS]
        assert len(keys) == len(set(keys)), "Duplicate driver keys found"

    def test_known_drivers_present(self):
        expected = {
            "postgresql", "oracle", "sqlserver", "mysql",
            "snowflake", "bigquery", "redshift", "azuresynapse",
            "sqlite", "custom",
        }
        assert expected == set(DRIVER_BY_KEY.keys())

    def test_get_driver_returns_correct_entry(self):
        driver = get_driver("postgresql")
        assert driver.default_port == 5432
        assert "psycopg2-binary" in driver.required_packages

    def test_get_driver_raises_for_unknown_key(self):
        with pytest.raises(KeyError, match="Unknown database driver key"):
            get_driver("nonexistent_db")

    def test_custom_driver_has_no_dialect(self):
        driver = get_driver("custom")
        assert driver.sqlalchemy_dialect is None
        assert driver.fields == ["connection_url"]

    def test_sqlite_needs_no_packages(self):
        driver = get_driver("sqlite")
        assert driver.required_packages == []

    def test_cloud_drivers_have_no_default_port(self):
        for key in ("snowflake", "bigquery"):
            driver = get_driver(key)
            assert driver.default_port is None, (
                f"Cloud driver '{key}' should have no default port"
            )


# ------------------------------------------------------------------ #
# DatabaseDataSource stub                                              #
# ------------------------------------------------------------------ #

class TestDatabaseDataSourceStub:
    def test_raises_for_wrong_source_type(self):
        config = DataSourceConfig(source_type="file")
        with pytest.raises(DataSourceError, match="source_type='database'"):
            DatabaseDataSource(config)

    def test_source_type(self):
        config = DataSourceConfig(source_type="database", driver_key="postgresql")
        src = DatabaseDataSource(config)
        assert src.source_type == "database"

    def test_display_name_uses_connection_name(self):
        config = DataSourceConfig(
            source_type="database",
            driver_key="postgresql",
            connection_name="DOT Prod",
            table_or_view="iri_survey",
        )
        src = DatabaseDataSource(config)
        assert "DOT Prod" in src.display_name
        assert "iri_survey" in src.display_name

    def test_methods_raise_not_implemented(self):
        config = DataSourceConfig(source_type="database", driver_key="postgresql")
        src = DatabaseDataSource(config)
        with pytest.raises(NotImplementedError):
            src.get_available_columns()
        with pytest.raises(NotImplementedError):
            src.load_data("x", "y")
        with pytest.raises(NotImplementedError):
            src.detect_routes("route")
        with pytest.raises(NotImplementedError):
            src.get_traceability_info()
