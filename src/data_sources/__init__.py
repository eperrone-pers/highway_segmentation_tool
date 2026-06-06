"""Data source abstraction layer for highway segmentation tool.

Provides a unified interface for loading input data from different sources
(CSV files, databases, GIS REST endpoints) without changing the analysis
pipeline downstream.
"""

from data_sources.base import DataSourceBase, DataSourceConfig
from data_sources.registry import get_data_source

__all__ = [
    "DataSourceBase",
    "DataSourceConfig",
    "get_data_source",
]
