"""Unit tests for the data_sources package."""

import os
from unittest.mock import MagicMock, patch

import pytest
import pandas as pd

from data_sources.base import DataSourceConfig, DataSourceError
from data_sources.registry import get_data_source
from data_sources.file_source import FileDataSource
from data_sources.database_source import DatabaseDataSource, _drop_lob_columns
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
    @pytest.mark.unit
    def test_defaults_to_file_source(self):
        config = DataSourceConfig()
        assert config.source_type == "file"

    @pytest.mark.unit
    def test_file_config_fields(self, csv_file):
        config = DataSourceConfig(source_type="file", file_path=str(csv_file))
        assert config.source_type == "file"
        assert config.file_path == str(csv_file)

    @pytest.mark.unit
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
    @pytest.mark.unit
    def test_raises_if_no_file_path(self):
        config = DataSourceConfig(source_type="file", file_path=None)
        with pytest.raises(DataSourceError, match="file_path"):
            FileDataSource(config)

    @pytest.mark.unit
    def test_raises_if_file_missing(self, tmp_path):
        config = DataSourceConfig(
            source_type="file", file_path=str(tmp_path / "missing.csv")
        )
        with pytest.raises(DataSourceError, match="not found"):
            FileDataSource(config)

    @pytest.mark.unit
    def test_source_type(self, file_config):
        src = FileDataSource(file_config)
        assert src.source_type == "file"

    @pytest.mark.unit
    def test_display_name_is_filename(self, file_config, csv_file):
        src = FileDataSource(file_config)
        assert src.display_name == csv_file.name

    @pytest.mark.unit
    def test_get_available_columns(self, file_config):
        src = FileDataSource(file_config)
        cols = src.get_available_columns()
        assert cols == ["milepoint", "iri", "route"]

    @pytest.mark.unit
    def test_load_data_returns_dataframe(self, file_config):
        src = FileDataSource(file_config)
        df = src.load_data(x_col="milepoint", y_col="iri")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5

    @pytest.mark.unit
    def test_load_data_all_string_dtype(self, file_config):
        src = FileDataSource(file_config)
        df = src.load_data(x_col="milepoint", y_col="iri")
        for col in df.columns:
            assert pd.api.types.is_string_dtype(df[col]), (
                f"Column '{col}' should be string dtype, got {df[col].dtype}"
            )

    @pytest.mark.unit
    def test_load_data_filter_by_selected_routes(self, file_config):
        src = FileDataSource(file_config)
        df = src.load_data(
            x_col="milepoint", y_col="iri",
            route_col="route", selected_routes=["US101"]
        )
        assert len(df) == 3
        assert df["route"].unique().tolist() == ["US101"]

    @pytest.mark.unit
    def test_load_data_no_filter_returns_all(self, file_config):
        src = FileDataSource(file_config)
        df = src.load_data(x_col="milepoint", y_col="iri", route_col="route")
        assert len(df) == 5

    @pytest.mark.unit
    def test_detect_routes(self, file_config):
        src = FileDataSource(file_config)
        routes = src.detect_routes("route")
        assert routes == ["I5", "US101"]

    @pytest.mark.unit
    def test_detect_routes_sorted(self, tmp_path):
        p = tmp_path / "routes.csv"
        p.write_text("mp,iri,route\n0,80,Z_Route\n1,85,A_Route\n2,90,M_Route\n")
        src = FileDataSource(DataSourceConfig(source_type="file", file_path=str(p)))
        assert src.detect_routes("route") == ["A_Route", "M_Route", "Z_Route"]

    @pytest.mark.unit
    def test_detect_routes_excludes_blank(self, tmp_path):
        p = tmp_path / "blanks.csv"
        p.write_text("mp,iri,route\n0,80,US101\n1,85,\n2,90,US101\n")
        src = FileDataSource(DataSourceConfig(source_type="file", file_path=str(p)))
        routes = src.detect_routes("route")
        assert "" not in routes
        assert "US101" in routes

    @pytest.mark.unit
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
    @pytest.mark.unit
    def test_file_source_returns_file_data_source(self, file_config):
        src = get_data_source(file_config)
        assert isinstance(src, FileDataSource)

    @pytest.mark.unit
    def test_database_source_returns_database_data_source(self):
        config = DataSourceConfig(
            source_type="database", driver_key="postgresql"
        )
        src = get_data_source(config)
        assert isinstance(src, DatabaseDataSource)

    @pytest.mark.unit
    def test_unknown_source_type_raises(self):
        config = DataSourceConfig(source_type="ftp")
        with pytest.raises(DataSourceError, match="Unknown source_type"):
            get_data_source(config)


# ------------------------------------------------------------------ #
# Driver registry                                                      #
# ------------------------------------------------------------------ #

class TestDriverRegistry:
    @pytest.mark.unit
    def test_all_drivers_have_required_fields(self):
        required_attrs = [
            "driver_key", "display_name", "fields", "required_packages"
        ]
        for driver in DATABASE_DRIVERS:
            for attr in required_attrs:
                assert hasattr(driver, attr), (
                    f"Driver '{driver.driver_key}' missing attribute '{attr}'"
                )

    @pytest.mark.unit
    def test_driver_keys_are_unique(self):
        keys = [d.driver_key for d in DATABASE_DRIVERS]
        assert len(keys) == len(set(keys)), "Duplicate driver keys found"

    @pytest.mark.unit
    def test_known_drivers_present(self):
        expected = {
            "postgresql", "oracle", "sqlserver", "mysql",
            "snowflake", "bigquery", "redshift", "azuresynapse",
            "sqlite", "custom",
        }
        assert expected == set(DRIVER_BY_KEY.keys())

    @pytest.mark.unit
    def test_get_driver_returns_correct_entry(self):
        driver = get_driver("postgresql")
        assert driver.default_port == 5432
        assert "psycopg2-binary" in driver.required_packages

    @pytest.mark.unit
    def test_get_driver_raises_for_unknown_key(self):
        with pytest.raises(KeyError, match="Unknown database driver key"):
            get_driver("nonexistent_db")

    @pytest.mark.unit
    def test_custom_driver_has_no_dialect(self):
        driver = get_driver("custom")
        assert driver.sqlalchemy_dialect is None
        assert driver.fields == ["connection_url"]

    @pytest.mark.unit
    def test_sqlite_needs_no_packages(self):
        driver = get_driver("sqlite")
        assert driver.required_packages == []

    @pytest.mark.unit
    def test_cloud_drivers_have_no_default_port(self):
        for key in ("snowflake", "bigquery"):
            driver = get_driver(key)
            assert driver.default_port is None, (
                f"Cloud driver '{key}' should have no default port"
            )


# ------------------------------------------------------------------ #
# DatabaseDataSource                                                   #
# ------------------------------------------------------------------ #

def _db_config(**kwargs) -> DataSourceConfig:
    """Minimal database config for testing."""
    defaults = dict(
        source_type="database",
        driver_key="postgresql",
        host="localhost",
        port=5432,
        database="pavement",
        table_or_view="iri_survey",
        username="analyst",
    )
    defaults.update(kwargs)
    return DataSourceConfig(**defaults)


def _make_mock_engine(columns=None, schema_names=None,
                      table_names=None, view_names=None):
    """Build a mock SQLAlchemy engine with a wired inspector.

    Returns ``(mock_engine, inspector, mock_conn)``. Patch
    ``sqlalchemy.inspect`` to return the inspector, and patch
    ``pandas.read_sql`` to control query results.
    """
    columns = columns or [{"name": "milepoint"}, {"name": "iri"}, {"name": "route"}]
    schema_names = schema_names or ["public"]
    table_names = table_names or ["iri_survey"]
    view_names = view_names or []

    inspector = MagicMock()
    inspector.get_columns.return_value = columns
    inspector.get_schema_names.return_value = schema_names
    inspector.get_table_names.return_value = table_names
    inspector.get_view_names.return_value = view_names

    mock_conn = MagicMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    return mock_engine, inspector, mock_conn


class TestDatabaseDataSource:
    @pytest.mark.unit
    def test_raises_for_wrong_source_type(self):
        config = DataSourceConfig(source_type="file")
        with pytest.raises(DataSourceError, match="source_type='database'"):
            DatabaseDataSource(config)

    @pytest.mark.unit
    def test_raises_without_driver_key(self):
        config = DataSourceConfig(source_type="database", driver_key="")
        with pytest.raises(DataSourceError, match="driver_key"):
            DatabaseDataSource(config)

    @pytest.mark.unit
    def test_source_type(self):
        src = DatabaseDataSource(_db_config())
        assert src.source_type == "database"

    @pytest.mark.unit
    def test_display_name_uses_connection_name(self):
        cfg = _db_config(connection_name="DOT Prod", table_or_view="iri_survey")
        src = DatabaseDataSource(cfg)
        assert "DOT Prod" in src.display_name
        assert "iri_survey" in src.display_name

    @pytest.mark.unit
    def test_display_name_falls_back_to_driver_key(self):
        cfg = _db_config(connection_name="", table_or_view="")
        src = DatabaseDataSource(cfg)
        assert "postgresql" in src.display_name

    @pytest.mark.unit
    def test_get_traceability_info_no_password(self):
        cfg = _db_config()
        cfg.extra["password"] = "secret"
        src = DatabaseDataSource(cfg)
        info = src.get_traceability_info()
        assert info["source_type"] == "database"
        assert info["driver"] == "postgresql"
        assert info["host"] == "localhost"
        assert "password" not in info
        assert "secret" not in str(info)

    # -- get_available_columns --

    @pytest.mark.unit
    def test_get_available_columns_returns_column_names(self):
        src = DatabaseDataSource(_db_config())
        engine, inspector, _ = _make_mock_engine()
        src._engine = engine
        with patch("sqlalchemy.inspect", return_value=inspector):
            cols = src.get_available_columns()
        assert cols == ["milepoint", "iri", "route"]

    @pytest.mark.unit
    def test_get_available_columns_raises_without_table(self):
        src = DatabaseDataSource(_db_config(table_or_view=""))
        src._engine = MagicMock()
        with pytest.raises(DataSourceError, match="No table or view"):
            src.get_available_columns()

    @pytest.mark.unit
    def test_get_available_columns_wraps_exceptions(self):
        src = DatabaseDataSource(_db_config())
        engine, inspector, _ = _make_mock_engine()
        inspector.get_columns.side_effect = RuntimeError("DB down")
        src._engine = engine
        with patch("sqlalchemy.inspect", return_value=inspector):
            with pytest.raises(DataSourceError, match="Could not retrieve columns"):
                src.get_available_columns()

    # -- get_available_schemas --

    @pytest.mark.unit
    def test_get_available_schemas(self):
        src = DatabaseDataSource(_db_config())
        engine, inspector, _ = _make_mock_engine(schema_names=["public", "pavement"])
        src._engine = engine
        with patch("sqlalchemy.inspect", return_value=inspector):
            schemas = src.get_available_schemas()
        assert schemas == ["pavement", "public"]

    # -- get_available_tables_and_views --

    @pytest.mark.unit
    def test_get_available_tables_and_views(self):
        src = DatabaseDataSource(_db_config())
        engine, inspector, _ = _make_mock_engine(
            table_names=["iri_survey", "pci_data"],
            view_names=["v_all_routes"],
        )
        src._engine = engine
        with patch("sqlalchemy.inspect", return_value=inspector):
            result = src.get_available_tables_and_views()
        names = [name for name, kind in result]
        kinds = [kind for name, kind in result]
        assert "iri_survey" in names
        assert "pci_data" in names
        assert "v_all_routes" in names
        assert "TABLE" in kinds
        assert "VIEW" in kinds

    # -- load_data --

    @pytest.mark.unit
    def test_load_data_returns_all_columns_string_dtype(self):
        src = DatabaseDataSource(_db_config())
        src._engine = MagicMock()
        raw_df = pd.DataFrame({
            "milepoint": ["0.0", "0.1"],
            "iri": [85.0, 90.2],          # numeric — must be cast to str
            "route": ["US101", "US101"],
            "surface_type": ["AC", "AC"],  # extra column; must be present for attribute breaks
        })
        with patch("pandas.read_sql", return_value=raw_df):
            with patch("sqlalchemy.text", return_value=MagicMock()):
                with patch("sqlalchemy.column", side_effect=lambda c: c):
                    with patch("sqlalchemy.table", return_value="iri_survey"):
                        df = src.load_data(x_col="milepoint", y_col="iri", route_col="route")
        assert "surface_type" in df.columns, "All columns must be returned for attribute break selection"
        for col in df.columns:
            assert pd.api.types.is_string_dtype(df[col]), (
                f"Column '{col}' should be string dtype, got {df[col].dtype}"
            )

    @pytest.mark.unit
    def test_load_data_raises_without_table_and_query(self):
        src = DatabaseDataSource(_db_config(table_or_view=""))
        src._engine = MagicMock()
        with pytest.raises(DataSourceError, match="No table/view or custom SQL"):
            src.load_data("x", "y")

    @pytest.mark.unit
    def test_load_data_raises_if_required_column_missing(self):
        src = DatabaseDataSource(_db_config())
        src._engine = MagicMock()
        df_without_iri = pd.DataFrame({"milepoint": ["0.0"], "route": ["US101"]})
        with patch("pandas.read_sql", return_value=df_without_iri):
            with patch("sqlalchemy.text", return_value=MagicMock()):
                with patch("sqlalchemy.column", side_effect=lambda c: c):
                    with patch("sqlalchemy.table", return_value="iri_survey"):
                        with pytest.raises(DataSourceError, match="Required column 'iri'"):
                            src.load_data(x_col="milepoint", y_col="iri")

    # -- detect_routes --

    @pytest.mark.unit
    def test_detect_routes_returns_sorted_unique(self):
        src = DatabaseDataSource(_db_config())
        src._engine = MagicMock()
        raw_df = pd.DataFrame({"route": ["US101", "I5", "US101", "SR99"]})
        with patch("pandas.read_sql", return_value=raw_df):
            with patch("sqlalchemy.text", return_value=MagicMock()):
                with patch("sqlalchemy.column", side_effect=lambda c: c):
                    with patch("sqlalchemy.table", return_value="iri_survey"):
                        routes = src.detect_routes("route")
        assert routes == ["I5", "SR99", "US101"]

    @pytest.mark.unit
    def test_detect_routes_raises_without_table(self):
        src = DatabaseDataSource(_db_config(table_or_view=""))
        src._engine = MagicMock()
        with pytest.raises(DataSourceError, match="No table/view or custom SQL"):
            src.detect_routes("route")

    # -- password retrieval --

    @pytest.mark.unit
    def test_get_password_from_env_var(self):
        src = DatabaseDataSource(_db_config())
        with patch.dict(os.environ, {"HST_DB_PASSWORD": "env_secret"}):
            with patch("keyring.get_password", return_value=None):
                pwd = src._get_password()
        assert pwd == "env_secret"

    @pytest.mark.unit
    def test_get_password_from_extra(self):
        cfg = _db_config()
        cfg.extra["password"] = "extra_secret"
        src = DatabaseDataSource(cfg)
        with patch.dict(os.environ, {}, clear=True):
            with patch("keyring.get_password", return_value=None):
                pwd = src._get_password()
        assert pwd == "extra_secret"

    @pytest.mark.unit
    def test_get_password_keyring_wins_over_env(self):
        src = DatabaseDataSource(_db_config())
        with patch.dict(os.environ, {"HST_DB_PASSWORD": "env_secret"}):
            with patch("keyring.get_password", return_value="keyring_secret"):
                pwd = src._get_password()
        assert pwd == "keyring_secret"

    # -- _check_required_packages --

    @pytest.mark.unit
    def test_check_required_packages_raises_for_missing(self):
        src = DatabaseDataSource(_db_config(driver_key="postgresql"))
        with patch("importlib.import_module", side_effect=ImportError("no module")):
            with pytest.raises(DataSourceError, match="Missing required package"):
                src._check_required_packages()

    @pytest.mark.unit
    def test_check_required_packages_custom_skips_check(self):
        src = DatabaseDataSource(_db_config(driver_key="custom"))
        src._check_required_packages()  # must not raise

    @pytest.mark.unit
    def test_check_required_packages_sqlite_skips_check(self):
        src = DatabaseDataSource(_db_config(driver_key="sqlite"))
        src._check_required_packages()  # required_packages=[], nothing to import

    # -- _build_connection_url --

    @pytest.mark.unit
    def test_build_connection_url_sqlite(self):
        cfg = _db_config(driver_key="sqlite")
        cfg.extra["file_path"] = "/tmp/test.db"
        src = DatabaseDataSource(cfg)
        url = src._build_connection_url()
        assert "sqlite" in str(url)
        assert "/tmp/test.db" in str(url)

    @pytest.mark.unit
    def test_build_connection_url_custom_raises_without_url(self):
        cfg = _db_config(driver_key="custom")
        cfg.extra = {}
        src = DatabaseDataSource(cfg)
        with pytest.raises(DataSourceError, match="connection_url"):
            src._build_connection_url()

    @pytest.mark.unit
    def test_build_connection_url_custom_uses_extra(self):
        cfg = _db_config(driver_key="custom")
        cfg.extra["connection_url"] = "postgresql://user:pw@host/db"
        src = DatabaseDataSource(cfg)
        url = src._build_connection_url()
        assert url == "postgresql://user:pw@host/db"


# ------------------------------------------------------------------ #
# _drop_lob_columns helper                                             #
# ------------------------------------------------------------------ #

class TestDropLobColumns:
    @pytest.mark.unit
    def test_drops_bytes_column(self):
        df = pd.DataFrame({
            "milepoint": [0.0, 0.1],
            "iri": [85.0, 90.2],
            "geom": [b"\x00\x01", b"\x00\x02"],  # BLOB
        })
        result = _drop_lob_columns(df)
        assert "geom" not in result.columns
        assert "milepoint" in result.columns
        assert "iri" in result.columns

    @pytest.mark.unit
    def test_drops_memoryview_column(self):
        df = pd.DataFrame({
            "milepoint": [0.0],
            "shape": [memoryview(b"\x00")],
        })
        result = _drop_lob_columns(df)
        assert "shape" not in result.columns

    @pytest.mark.unit
    def test_keeps_string_object_columns(self):
        df = pd.DataFrame({
            "milepoint": [0.0],
            "surface": ["AC"],
        })
        result = _drop_lob_columns(df)
        assert "surface" in result.columns

    @pytest.mark.unit
    def test_passes_through_no_lob(self):
        df = pd.DataFrame({"a": [1.0], "b": ["x"]})
        result = _drop_lob_columns(df)
        assert list(result.columns) == ["a", "b"]

    @pytest.mark.unit
    def test_handles_all_null_column(self):
        df = pd.DataFrame({"milepoint": [0.0], "geom": [None]})
        result = _drop_lob_columns(df)
        assert "geom" in result.columns  # null-only columns are not dropped
