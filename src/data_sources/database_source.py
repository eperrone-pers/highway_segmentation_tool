"""Database data source implementation (Phase 1 — Step 2).

This module is a stub. Full implementation follows in Step 2 of the
data source connectivity plan, which covers SQLAlchemy engine creation,
table/view browsing via the inspection API, and parameterized data
loading.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from data_sources.base import DataSourceBase, DataSourceConfig, DataSourceError

_logger = logging.getLogger(__name__)


class DatabaseDataSource(DataSourceBase):
    """Data source backed by a relational database via SQLAlchemy.

    Supports any database in ``driver_registry.DATABASE_DRIVERS``.
    Passwords are never stored — retrieved from the system keyring or
    prompted at runtime.

    Note:
        This class is a stub pending Step 2 implementation. All methods
        raise ``NotImplementedError`` until Step 2 is complete.
    """

    def __init__(self, config: DataSourceConfig) -> None:
        if config.source_type != "database":
            raise DataSourceError(
                f"DatabaseDataSource requires source_type='database', "
                f"got '{config.source_type}'."
            )
        self._config = config

    @property
    def source_type(self) -> str:
        return "database"

    @property
    def display_name(self) -> str:
        name = self._config.connection_name or self._config.driver_key or "database"
        table = self._config.table_or_view
        return f"{name} / {table}" if table else name

    def get_available_columns(self) -> List[str]:
        raise NotImplementedError("DatabaseDataSource is not yet implemented.")

    def load_data(
        self,
        x_col: str,
        y_col: str,
        route_col: Optional[str] = None,
        selected_routes: Optional[List[str]] = None,
        must_break_cols: Optional[List[str]] = None,
        secondary_break_cols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        raise NotImplementedError("DatabaseDataSource is not yet implemented.")

    def detect_routes(self, route_col: str) -> List[str]:
        raise NotImplementedError("DatabaseDataSource is not yet implemented.")

    def get_traceability_info(self) -> Dict[str, Any]:
        raise NotImplementedError("DatabaseDataSource is not yet implemented.")
