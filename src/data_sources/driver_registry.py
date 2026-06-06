"""Registry of well-known database driver configurations.

To add support for a new database type, append a ``DatabaseDriverConfig``
entry to ``DATABASE_DRIVERS``. No other files need to change.

The ``fields`` list on each entry drives the GUI connection form — only
the fields listed are shown. Cloud databases that don't use a host/port
(Snowflake, BigQuery) declare different fields and the form adapts
automatically.

The ``custom`` entry at the end is the escape hatch for any database
type not listed here — the user supplies a raw SQLAlchemy connection URL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DatabaseDriverConfig:
    """Describes a supported database driver.

    Attributes:
        driver_key: Unique identifier used in ``DataSourceConfig.driver_key``
            and in run-spec JSON.
        display_name: Label shown in the GUI driver dropdown.
        sqlalchemy_dialect: SQLAlchemy dialect string used to build the
            connection URL (e.g. ``"postgresql+psycopg2"``). ``None`` for
            the custom URL escape hatch.
        default_port: Default port pre-filled in the GUI form. ``None``
            for drivers that don't use a port.
        required_packages: Python packages that must be installed for this
            driver. Checked at connection time; missing packages surface a
            clear install message.
        fields: Ordered list of field names shown in the GUI connection
            form. Controls which inputs are rendered — cloud databases
            use different fields than traditional servers.
        notes: Optional human-readable note shown below the form
            (e.g. authentication instructions).
    """

    driver_key: str
    display_name: str
    sqlalchemy_dialect: Optional[str]
    default_port: Optional[int]
    required_packages: List[str]
    fields: List[str]
    notes: str = ""


DATABASE_DRIVERS: List[DatabaseDriverConfig] = [
    # ------------------------------------------------------------------ #
    # Core enterprise                                                      #
    # ------------------------------------------------------------------ #
    DatabaseDriverConfig(
        driver_key="postgresql",
        display_name="PostgreSQL",
        sqlalchemy_dialect="postgresql+psycopg2",
        default_port=5432,
        required_packages=["psycopg2-binary"],
        fields=["host", "port", "database", "schema", "username"],
        notes="PostGIS spatial extensions are supported if installed on the server.",
    ),
    DatabaseDriverConfig(
        driver_key="oracle",
        display_name="Oracle",
        sqlalchemy_dialect="oracle+cx_oracle",
        default_port=1521,
        required_packages=["cx_Oracle"],
        fields=["host", "port", "database", "schema", "username"],
    ),
    DatabaseDriverConfig(
        driver_key="sqlserver",
        display_name="SQL Server",
        sqlalchemy_dialect="mssql+pyodbc",
        default_port=1433,
        required_packages=["pyodbc"],
        fields=["host", "port", "database", "schema", "username"],
        notes="Requires ODBC Driver 17 or 18 for SQL Server.",
    ),
    DatabaseDriverConfig(
        driver_key="mysql",
        display_name="MySQL / MariaDB",
        sqlalchemy_dialect="mysql+pymysql",
        default_port=3306,
        required_packages=["pymysql"],
        fields=["host", "port", "database", "schema", "username"],
    ),
    # ------------------------------------------------------------------ #
    # Cloud / analytics                                                    #
    # ------------------------------------------------------------------ #
    DatabaseDriverConfig(
        driver_key="snowflake",
        display_name="Snowflake",
        sqlalchemy_dialect="snowflake",
        default_port=None,
        required_packages=["snowflake-sqlalchemy"],
        fields=["account", "database", "schema", "username"],
        notes="Use your Snowflake account identifier (e.g. xy12345.us-east-1).",
    ),
    DatabaseDriverConfig(
        driver_key="bigquery",
        display_name="Google BigQuery",
        sqlalchemy_dialect="bigquery",
        default_port=None,
        required_packages=["sqlalchemy-bigquery"],
        fields=["project", "dataset", "username"],
        notes="Authenticate via Google Application Default Credentials.",
    ),
    DatabaseDriverConfig(
        driver_key="redshift",
        display_name="Amazon Redshift",
        sqlalchemy_dialect="redshift+redshift_connector",
        default_port=5439,
        required_packages=["redshift-connector", "sqlalchemy-redshift"],
        fields=["host", "port", "database", "schema", "username"],
    ),
    DatabaseDriverConfig(
        driver_key="azuresynapse",
        display_name="Azure Synapse",
        sqlalchemy_dialect="mssql+pyodbc",
        default_port=1433,
        required_packages=["pyodbc"],
        fields=["host", "port", "database", "schema", "username"],
        notes="Requires ODBC Driver 17 or 18 for SQL Server.",
    ),
    # ------------------------------------------------------------------ #
    # Lightweight / local                                                  #
    # ------------------------------------------------------------------ #
    DatabaseDriverConfig(
        driver_key="sqlite",
        display_name="SQLite",
        sqlalchemy_dialect="sqlite",
        default_port=None,
        required_packages=[],
        fields=["file_path"],
        notes="No server required — connects directly to a local .db file.",
    ),
    # ------------------------------------------------------------------ #
    # Escape hatch                                                         #
    # ------------------------------------------------------------------ #
    DatabaseDriverConfig(
        driver_key="custom",
        display_name="Custom (SQLAlchemy URL)",
        sqlalchemy_dialect=None,
        default_port=None,
        required_packages=[],
        fields=["connection_url"],
        notes="Enter any valid SQLAlchemy connection URL directly.",
    ),
]

# Lookup by driver_key for O(1) access.
DRIVER_BY_KEY: dict = {d.driver_key: d for d in DATABASE_DRIVERS}


def get_driver(driver_key: str) -> DatabaseDriverConfig:
    """Return the ``DatabaseDriverConfig`` for ``driver_key``.

    Args:
        driver_key: Key matching a ``DatabaseDriverConfig.driver_key``
            in ``DATABASE_DRIVERS``.

    Returns:
        The matching ``DatabaseDriverConfig``.

    Raises:
        KeyError: If ``driver_key`` is not registered.
    """
    if driver_key not in DRIVER_BY_KEY:
        raise KeyError(
            f"Unknown database driver key: '{driver_key}'. "
            f"Available keys: {list(DRIVER_BY_KEY)}"
        )
    return DRIVER_BY_KEY[driver_key]
