"""Abstract base class and configuration dataclass for data sources."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

_logger = logging.getLogger(__name__)


@dataclass
class DataSourceConfig:
    """Configuration for any data source type.

    The ``source_type`` field is the discriminator: ``"file"`` for CSV
    sources, ``"database"`` for relational databases. Additional fields
    are source-type specific and passed through to the relevant
    ``DataSourceBase`` implementation.

    Attributes:
        source_type: Discriminator — ``"file"`` or ``"database"``.
        file_path: Absolute path to the CSV file (file sources only).
        driver_key: Driver key from ``driver_registry.DATABASE_DRIVERS``
            (database sources only).
        host: Database server host (database sources only).
        port: Database server port (database sources only).
        database: Database/catalog name (database sources only).
        schema: Schema name within the database (optional).
        table_or_view: Table or view to query (database sources only).
        custom_sql_query: Custom SQL query overriding ``table_or_view``
            (database sources only).
        username: Database username (database sources only).
        connection_name: Human-readable label for saved connections
            (e.g. "State DOT Oracle Prod").
        extra: Driver-specific fields not covered above (e.g. Snowflake
            account identifier, BigQuery project ID).
    """

    source_type: str = "file"
    file_path: Optional[str] = None
    driver_key: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    schema: Optional[str] = None
    table_or_view: Optional[str] = None
    custom_sql_query: Optional[str] = None
    username: Optional[str] = None
    connection_name: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


class DataSourceBase(ABC):
    """Abstract base class for all data source implementations.

    Concrete subclasses (``FileDataSource``, ``DatabaseDataSource``, etc.)
    implement this interface so the rest of the application can load data
    without knowing the underlying source type.

    The three core methods mirror the three operations ``file_manager.py``
    currently performs against CSV files:

    - ``get_available_columns`` — discover what columns exist (used to
      populate the X/Y/Route column dropdowns in the GUI).
    - ``load_data`` — fetch the full raw dataset as a DataFrame.
    - ``detect_routes`` — list available route IDs for multi-route mode.

    ``get_traceability_info`` provides source-specific metadata for the
    results JSON ``input_file_info`` section.
    """

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Short identifier for the source type (e.g. ``"file"``, ``"database"``)."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable label for log messages and UI status text."""

    @abstractmethod
    def get_available_columns(self) -> List[str]:
        """Return the list of column names available from this source.

        For file sources this reads CSV headers without loading data.
        For database sources this runs a zero-row query against the
        selected table/view.

        Returns:
            List of column name strings.

        Raises:
            DataSourceError: If the source cannot be reached or the
                column list cannot be retrieved.
        """

    @abstractmethod
    def load_data(
        self,
        x_col: str,
        y_col: str,
        route_col: Optional[str] = None,
        selected_routes: Optional[List[str]] = None,
        must_break_cols: Optional[List[str]] = None,
        secondary_break_cols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Load raw data as a DataFrame with all values as strings.

        Returning string dtype matches the existing CSV loading behaviour
        in ``file_manager.py`` and ensures downstream type coercion logic
        runs identically regardless of source type.

        Args:
            x_col: Name of the distance/milepoint column.
            y_col: Name of the condition measurement column.
            route_col: Name of the route identifier column, or ``None``
                for single-route mode.
            selected_routes: If provided, only rows whose ``route_col``
                value is in this list are returned. ``None`` means all
                routes.
            must_break_cols: Additional columns to include (early
                attribute break columns).
            secondary_break_cols: Additional columns to include (late
                attribute break columns).

        Returns:
            DataFrame with string dtype columns. At minimum contains
            ``x_col`` and ``y_col``; includes ``route_col`` and any
            attribute break columns when supplied.

        Raises:
            DataSourceError: If the data cannot be loaded.
        """

    @abstractmethod
    def detect_routes(self, route_col: str) -> List[str]:
        """Return the distinct route ID values for ``route_col``.

        Used to populate the route filter dialog in the GUI.

        Args:
            route_col: Name of the route identifier column.

        Returns:
            Sorted list of route ID strings, excluding blank/null values.

        Raises:
            DataSourceError: If routes cannot be retrieved.
        """

    @abstractmethod
    def get_traceability_info(self) -> Dict[str, Any]:
        """Return source metadata for the results JSON ``input_file_info``.

        The dict must NOT include passwords or other credentials. Fields
        vary by source type — file sources include ``data_file_path`` and
        ``data_file_size_bytes``; database sources include ``driver``,
        ``host``, ``table_or_view``, etc.

        Returns:
            Dict of serialisable metadata fields.
        """


class DataSourceError(Exception):
    """Raised when a data source operation fails.

    Wraps underlying driver/IO exceptions with a user-friendly message
    so callers can surface it directly in the GUI or CLI without
    inspecting driver-specific exception types.
    """
