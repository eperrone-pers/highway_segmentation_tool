"""Database data source implementation via SQLAlchemy."""

from __future__ import annotations

import importlib
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from data_sources.base import DataSourceBase, DataSourceConfig, DataSourceError

_logger = logging.getLogger(__name__)

# Keyring service name used to store/retrieve database passwords.
_KEYRING_SERVICE = "highway_segmentation_tool"

# Environment variable checked as a password fallback for CLI/headless use.
_PASSWORD_ENV_VAR = "HST_DB_PASSWORD"

# Some packages install under a different name than their pip distribution name.
# e.g. "psycopg2-binary" installs as the "psycopg2" module.
_PACKAGE_IMPORT_NAMES: Dict[str, str] = {
    "psycopg2-binary": "psycopg2",
    "sqlalchemy-bigquery": "sqlalchemy_bigquery",
    "snowflake-sqlalchemy": "snowflake.sqlalchemy",
    "redshift-connector": "redshift_connector",
    "sqlalchemy-redshift": "sqlalchemy_redshift",
}


class DatabaseDataSource(DataSourceBase):
    """Data source backed by a relational database via SQLAlchemy.

    Supports any database registered in ``driver_registry.DATABASE_DRIVERS``.
    The SQLAlchemy engine is created lazily on first use and cached for the
    lifetime of this instance.

    Passwords are never stored in settings files. Retrieval order:
    1. System keyring (keyed by ``connection_name`` or ``username``).
    2. ``HST_DB_PASSWORD`` environment variable.
    3. ``DataSourceConfig.extra["password"]`` — only for programmatic /
       test use; never persisted to disk.

    Args:
        config: A ``DataSourceConfig`` with ``source_type="database"``
            and a valid ``driver_key``.

    Raises:
        DataSourceError: If ``source_type`` is not ``"database"``, or if
            the driver key is not registered.
    """

    def __init__(self, config: DataSourceConfig) -> None:
        if config.source_type != "database":
            raise DataSourceError(
                f"DatabaseDataSource requires source_type='database', "
                f"got '{config.source_type}'."
            )
        if not config.driver_key:
            raise DataSourceError(
                "DatabaseDataSource requires a driver_key in config."
            )
        self._config = config
        self._engine: Any = None  # Lazy; created on first _get_engine() call.

    # ------------------------------------------------------------------ #
    # DataSourceBase properties                                            #
    # ------------------------------------------------------------------ #

    @property
    def source_type(self) -> str:
        return "database"

    @property
    def display_name(self) -> str:
        name = self._config.connection_name or self._config.driver_key or "database"
        table = self._config.table_or_view
        return f"{name} / {table}" if table else name

    # ------------------------------------------------------------------ #
    # DataSourceBase interface                                             #
    # ------------------------------------------------------------------ #

    def get_available_columns(self) -> List[str]:
        """Return column names from the configured table/view.

        Uses SQLAlchemy's reflection API — no database-specific queries.

        Returns:
            List of column name strings.

        Raises:
            DataSourceError: If the table cannot be inspected.
        """
        import sqlalchemy

        if not self._config.table_or_view:
            raise DataSourceError(
                "No table or view configured. Set DataSourceConfig.table_or_view."
            )
        try:
            engine = self._get_engine()
            inspector = sqlalchemy.inspect(engine)
            cols = inspector.get_columns(
                self._config.table_or_view,
                schema=self._config.schema or None,
            )
            return [col["name"] for col in cols]
        except DataSourceError:
            raise
        except Exception as exc:
            raise DataSourceError(
                f"Could not retrieve columns from "
                f"'{self._config.table_or_view}': {exc}"
            ) from exc

    def load_data(
        self,
        x_col: str,
        y_col: str,
        route_col: Optional[str] = None,
        selected_routes: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Load all scalar columns from the configured table/view.

        Mirrors ``pd.read_csv`` behaviour: every column is returned so
        the GUI can offer the full column list for attribute break
        selection after the data loads. Only row filtering is applied —
        ``SELECT *`` with an optional ``WHERE route IN (...)`` clause.

        LOB/BLOB/CLOB/binary columns are excluded automatically because
        they cannot be meaningfully cast to strings and are irrelevant to
        pavement segmentation.

        Args:
            x_col: Distance/milepoint column name (row validation only).
            y_col: Condition measurement column name (row validation only).
            route_col: Route identifier column for WHERE filtering.
            selected_routes: If provided, only rows for these routes are
                returned. ``None`` returns all rows.

        Returns:
            DataFrame with all non-LOB columns as string dtype.

        Raises:
            DataSourceError: If the query fails.
        """
        import sqlalchemy

        if not self._config.table_or_view and not self._config.custom_sql_query:
            raise DataSourceError(
                "No table/view or custom SQL query configured."
            )

        try:
            engine = self._get_engine()
            if self._config.custom_sql_query:
                query = sqlalchemy.text(self._config.custom_sql_query)
                with engine.connect() as conn:
                    df = pd.read_sql(query, conn)
            else:
                table_ref = self._table_identifier()
                sql = f"SELECT * FROM {table_ref}"

                params: Dict[str, Any] = {}
                if selected_routes and route_col:
                    placeholders = ", ".join(
                        f":route_{i}" for i in range(len(selected_routes))
                    )
                    sql += (
                        f" WHERE {sqlalchemy.column(route_col)}"
                        f" IN ({placeholders})"
                    )
                    params = {f"route_{i}": r for i, r in enumerate(selected_routes)}

                with engine.connect() as conn:
                    df = pd.read_sql(sqlalchemy.text(sql), conn, params=params)

            df = _drop_lob_columns(df)
            result = df.astype(str)

            for required_col in (x_col, y_col):
                if required_col not in result.columns:
                    raise DataSourceError(
                        f"Required column '{required_col}' not found in "
                        f"'{self._config.table_or_view}'. "
                        f"Available columns: {list(result.columns)}"
                    )

            return result

        except DataSourceError:
            raise
        except Exception as exc:
            raise DataSourceError(
                f"Failed to load data from '{self._config.table_or_view}': {exc}"
            ) from exc

    def get_row_count(self) -> int:
        """Return the number of rows in the configured table or view.

        Used to warn the user before loading a very large table.  Fails
        open — returns 0 on any error so the caller can still attempt to
        load the data.

        Returns:
            Row count, or 0 if the count cannot be determined.
        """
        import sqlalchemy

        if not self._config.table_or_view:
            return 0
        table_ref = self._table_identifier()
        sql = f"SELECT COUNT(*) FROM {table_ref}"
        try:
            engine = self._get_engine()
            with engine.connect() as conn:
                result = conn.execute(sqlalchemy.text(sql))
                row = result.fetchone()
                return int(row[0]) if row else 0
        except Exception as exc:
            _logger.debug("Could not determine row count for '%s': %s", self._config.table_or_view, exc)
            return 0

    def detect_routes(self, route_col: str) -> List[str]:
        """Return sorted distinct non-null route IDs from the table.

        Args:
            route_col: Name of the route identifier column.

        Returns:
            Sorted list of route ID strings.

        Raises:
            DataSourceError: If the query fails or no table is configured.
        """
        import sqlalchemy

        if not self._config.table_or_view and not self._config.custom_sql_query:
            raise DataSourceError(
                "No table/view or custom SQL query configured."
            )

        table_ref = self._table_identifier()
        col = sqlalchemy.column(route_col)
        sql = (
            f"SELECT DISTINCT {col} FROM {table_ref} "
            f"WHERE {col} IS NOT NULL"
        )
        try:
            engine = self._get_engine()
            with engine.connect() as conn:
                df = pd.read_sql(sqlalchemy.text(sql), conn)
            series = df.iloc[:, 0].astype(str).str.strip()
            routes = series[series != ""].unique().tolist()
            return sorted(routes)
        except DataSourceError:
            raise
        except Exception as exc:
            raise DataSourceError(
                f"Failed to detect routes in column '{route_col}': {exc}"
            ) from exc

    def get_traceability_info(self) -> Dict[str, Any]:
        """Return database metadata for the results JSON ``input_file_info``.

        Never includes the password or any credential.

        Returns:
            Dict with ``source_type``, ``driver``, ``host``, ``database``,
            ``schema``, ``table_or_view``, and ``username``.
        """
        cfg = self._config
        return {
            "source_type": "database",
            "driver": cfg.driver_key,
            "host": cfg.host,
            "port": cfg.port,
            "database": cfg.database,
            "schema": cfg.schema,
            "table_or_view": cfg.table_or_view,
            "username": cfg.username,
            "connection_name": cfg.connection_name,
        }

    # ------------------------------------------------------------------ #
    # Schema / table browsing (used by the GUI connection dialog)         #
    # ------------------------------------------------------------------ #

    def get_available_schemas(self) -> List[str]:
        """Return schema names visible to the connected user.

        Returns:
            Sorted list of schema name strings.

        Raises:
            DataSourceError: If the connection fails.
        """
        import sqlalchemy

        try:
            engine = self._get_engine()
            inspector = sqlalchemy.inspect(engine)
            return sorted(inspector.get_schema_names())
        except DataSourceError:
            raise
        except Exception as exc:
            raise DataSourceError(
                f"Could not retrieve schema names: {exc}"
            ) from exc

    def get_available_tables_and_views(
        self, schema: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """Return tables and views available in ``schema``.

        Args:
            schema: Schema name to inspect. ``None`` uses the default
                schema for the connected user.

        Returns:
            Sorted list of ``(name, kind)`` tuples where ``kind`` is
            ``"TABLE"`` or ``"VIEW"``.

        Raises:
            DataSourceError: If the connection fails.
        """
        import sqlalchemy

        resolved_schema = schema or self._config.schema or None
        try:
            engine = self._get_engine()
            inspector = sqlalchemy.inspect(engine)
            tables = [
                (t, "TABLE")
                for t in inspector.get_table_names(schema=resolved_schema)
            ]
            views = [
                (v, "VIEW")
                for v in inspector.get_view_names(schema=resolved_schema)
            ]
            return sorted(tables + views, key=lambda x: x[0])
        except DataSourceError:
            raise
        except Exception as exc:
            raise DataSourceError(
                f"Could not retrieve tables/views: {exc}"
            ) from exc

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _get_engine(self) -> Any:
        """Return a cached SQLAlchemy engine, creating it on first call.

        Raises:
            DataSourceError: If SQLAlchemy is not installed, required
                driver packages are missing, or the connection URL cannot
                be built.
        """
        if self._engine is not None:
            return self._engine

        try:
            import sqlalchemy as sa
        except ImportError as exc:
            raise DataSourceError(
                "SQLAlchemy is required for database connectivity. "
                "Install it with: pip install sqlalchemy"
            ) from exc

        self._check_required_packages()

        try:
            url = self._build_connection_url()
            self._engine = sa.create_engine(url)
            _logger.debug("Created SQLAlchemy engine for %s", self.display_name)
        except DataSourceError:
            raise
        except Exception as exc:
            raise DataSourceError(
                f"Could not create database engine: {exc}"
            ) from exc

        return self._engine

    def _check_required_packages(self) -> None:
        """Verify that the driver's required packages are importable.

        Raises:
            DataSourceError: Lists all missing packages with install hint.
        """
        from data_sources.driver_registry import get_driver

        if self._config.driver_key == "custom":
            return

        try:
            driver = get_driver(self._config.driver_key)
        except KeyError as exc:
            raise DataSourceError(str(exc)) from exc

        missing = []
        for pkg in driver.required_packages:
            bare = pkg.split(">=")[0].split("==")[0].split("[")[0]
            module = _PACKAGE_IMPORT_NAMES.get(bare, bare.replace("-", "_"))
            try:
                importlib.import_module(module)
            except ImportError:
                missing.append(pkg)

        if missing:
            raise DataSourceError(
                f"Missing required package(s) for {driver.display_name}: "
                f"{', '.join(missing)}. "
                f"Install with: pip install {' '.join(missing)}"
            )

    def _get_password(self) -> Optional[str]:
        """Retrieve the database password without storing it.

        Lookup order:
        1. System keyring (service=``_KEYRING_SERVICE``,
           username=``connection_name`` or ``username``).
        2. ``HST_DB_PASSWORD`` environment variable.
        3. ``config.extra["password"]`` (programmatic / test use only).

        Returns:
            Password string, or ``None`` if not found anywhere.
        """
        keyring_key = self._config.connection_name or self._config.username or ""

        # 1. System keyring
        try:
            import keyring as kr
            pwd = kr.get_password(_KEYRING_SERVICE, keyring_key)
            if pwd:
                return pwd
        except Exception:
            _logger.debug("Keyring lookup failed; falling back to env var.")

        # 2. Environment variable
        pwd = os.environ.get(_PASSWORD_ENV_VAR)
        if pwd:
            return pwd

        # 3. Programmatic / test extra field
        return self._config.extra.get("password")

    def _build_connection_url(self) -> Any:
        """Build a SQLAlchemy connection URL from config + driver registry.

        Returns:
            A ``sqlalchemy.engine.URL`` (or raw string for custom URLs).

        Raises:
            DataSourceError: If required fields are missing or the URL
                cannot be constructed.
        """
        import sqlalchemy
        from data_sources.driver_registry import get_driver

        cfg = self._config

        # Custom URL — use as-is
        if cfg.driver_key == "custom":
            url = cfg.extra.get("connection_url")
            if not url:
                raise DataSourceError(
                    "Custom driver requires a connection_url in config.extra."
                )
            return url

        # SQLite — file path, no credentials.
        # Accept the path from extra["file_path"] (GUI dialog), cfg.database
        # (recommended for CLI run-specs), or cfg.host (legacy fallback).
        if cfg.driver_key == "sqlite":
            file_path = cfg.extra.get("file_path") or cfg.database or cfg.host or ""
            return f"sqlite:///{file_path}"

        try:
            driver = get_driver(cfg.driver_key)
        except KeyError as exc:
            raise DataSourceError(str(exc)) from exc

        password = self._get_password()

        return sqlalchemy.engine.URL.create(
            drivername=driver.sqlalchemy_dialect,
            username=cfg.username,
            password=password,
            host=cfg.host,
            port=cfg.port,
            database=cfg.database,
        )

    def _table_identifier(self) -> str:
        """Return a schema-qualified table identifier string.

        Returns ``schema.table`` when a schema is set, otherwise just
        ``table``.
        """
        import sqlalchemy

        table = self._config.table_or_view or ""
        schema = self._config.schema

        if schema:
            return str(
                sqlalchemy.table(table, schema=schema)
            )
        return str(sqlalchemy.table(table))


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _drop_lob_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return df with LOB/BLOB/CLOB/binary columns removed.

    After ``pd.read_sql``, large-object columns arrive as ``object``
    dtype containing ``bytes`` or ``memoryview`` values. They cannot be
    cast to strings meaningfully and are irrelevant to pavement
    segmentation analysis.

    Args:
        df: Raw DataFrame from ``pd.read_sql``.

    Returns:
        DataFrame with binary/LOB columns dropped.
    """
    lob_cols = []
    for col in df.columns:
        if df[col].dtype != object:
            continue
        non_null = df[col].dropna()
        if non_null.empty:
            continue
        sample = non_null.iloc[0]
        if isinstance(sample, (bytes, memoryview, bytearray)):
            lob_cols.append(col)

    if lob_cols:
        _logger.debug("Dropping LOB/binary columns (not useful for analysis): %s", lob_cols)
        df = df.drop(columns=lob_cols)

    return df
