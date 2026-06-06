"""Data source abstraction layer for highway segmentation tool.

Provides a unified interface for loading input data from different sources
(CSV files, databases, GIS REST endpoints) without changing the analysis
pipeline downstream.
"""

from data_sources.base import DataSourceBase, DataSourceConfig, DataSourceError
from data_sources.registry import get_data_source
from data_sources.type_registry import (
    DataSourceTypeConfig,
    DATA_SOURCE_TYPES,
    get_source_type,
    get_display_names,
    get_type_by_display_name,
)

__all__ = [
    "DataSourceBase",
    "DataSourceConfig",
    "DataSourceError",
    "get_data_source",
    "DataSourceTypeConfig",
    "DATA_SOURCE_TYPES",
    "get_source_type",
    "get_display_names",
    "get_type_by_display_name",
]
