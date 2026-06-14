"""CSV file data source implementation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from data_sources.base import DataSourceBase, DataSourceConfig, DataSourceError

_logger = logging.getLogger(__name__)


class FileDataSource(DataSourceBase):
    """Data source backed by a local CSV file.

    This is a thin wrapper around the ``pd.read_csv`` calls that currently
    live in ``file_manager.py``. Behaviour is intentionally identical —
    data is loaded with ``dtype=str`` so downstream type coercion in the
    existing pipeline runs unchanged.

    Args:
        config: A ``DataSourceConfig`` with ``source_type="file"`` and a
            valid ``file_path``.

    Raises:
        DataSourceError: If ``config.file_path`` is ``None`` or the file
            does not exist.
    """

    def __init__(self, config: DataSourceConfig) -> None:
        if not config.file_path:
            raise DataSourceError("FileDataSource requires a file_path in config.")
        self._path = Path(config.file_path)
        if not self._path.exists():
            raise DataSourceError(f"Data file not found: {self._path}")

    @property
    def source_type(self) -> str:
        return "file"

    @property
    def display_name(self) -> str:
        return self._path.name

    def get_available_columns(self) -> List[str]:
        """Return column names by reading only the CSV header row.

        Returns:
            List of column name strings.

        Raises:
            DataSourceError: If the file cannot be read.
        """
        try:
            df = pd.read_csv(self._path, nrows=0)
            return list(df.columns)
        except Exception as exc:
            raise DataSourceError(
                f"Could not read columns from {self._path.name}: {exc}"
            ) from exc

    def load_data(
        self,
        x_col: str,
        y_col: str,
        route_col: Optional[str] = None,
        selected_routes: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Load the full CSV as a string-typed DataFrame.

        All columns are returned (matches ``pd.read_csv`` behaviour).
        The only filtering applied is row-level: when ``selected_routes``
        is provided, only rows for those routes are kept.

        Args:
            x_col: Distance/milepoint column name (validation only).
            y_col: Condition measurement column name (validation only).
            route_col: Route identifier column, or ``None``.
            selected_routes: If provided, filter to these route IDs only.

        Returns:
            Full DataFrame with all columns, string dtype.

        Raises:
            DataSourceError: If the file cannot be read.
        """
        try:
            df = pd.read_csv(self._path, dtype=str)
        except Exception as exc:
            raise DataSourceError(
                f"Could not load data from {self._path.name}: {exc}"
            ) from exc

        if selected_routes and route_col and route_col in df.columns:
            df = df[df[route_col].isin(selected_routes)].reset_index(drop=True)

        return df

    def detect_routes(self, route_col: str) -> List[str]:
        """Return sorted distinct route IDs from the CSV.

        Reads only the route column to avoid loading the full file.

        Args:
            route_col: Name of the route identifier column.

        Returns:
            Sorted list of non-blank route ID strings.

        Raises:
            DataSourceError: If the file cannot be read or the column
                does not exist.
        """
        try:
            df = pd.read_csv(
                self._path,
                usecols=[route_col],
                dtype={route_col: str},
            )
        except Exception as exc:
            raise DataSourceError(
                f"Could not read route column '{route_col}' from "
                f"{self._path.name}: {exc}"
            ) from exc

        routes = (
            df[route_col]
            .dropna()
            .str.strip()
            .replace("", pd.NA)
            .dropna()
            .unique()
            .tolist()
        )
        return sorted(routes)

    def get_traceability_info(self) -> Dict[str, Any]:
        """Return file metadata for the results JSON ``input_file_info``.

        Returns:
            Dict with ``source_type``, ``data_file_path``,
            ``data_file_name``, and ``data_file_size_bytes``.
        """
        size: Optional[int] = None
        try:
            size = self._path.stat().st_size
        except OSError:
            pass

        return {
            "source_type": "file",
            "data_file_path": str(self._path),
            "data_file_name": self._path.name,
            "data_file_size_bytes": size,
        }
