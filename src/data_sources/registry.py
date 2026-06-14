"""Factory for creating DataSourceBase instances from a DataSourceConfig."""

from __future__ import annotations

import logging

from data_sources.base import DataSourceBase, DataSourceConfig, DataSourceError

_logger = logging.getLogger(__name__)


def get_data_source(config: DataSourceConfig) -> DataSourceBase:
    """Return the appropriate ``DataSourceBase`` for ``config.source_type``.

    Args:
        config: A populated ``DataSourceConfig`` instance.

    Returns:
        A concrete ``DataSourceBase`` implementation ready to use.

    Raises:
        DataSourceError: If ``config.source_type`` is not recognised.
    """
    if config.source_type == "file":
        from data_sources.file_source import FileDataSource
        return FileDataSource(config)

    if config.source_type == "database":
        from data_sources.database_source import DatabaseDataSource
        return DatabaseDataSource(config)

    raise DataSourceError(
        f"Unknown source_type: '{config.source_type}'. "
        "Expected 'file' or 'database'."
    )
