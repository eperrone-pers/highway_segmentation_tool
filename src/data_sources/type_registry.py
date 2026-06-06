"""Registry of supported data source types.

To add a new source type, append a ``DataSourceTypeConfig`` entry to
``DATA_SOURCE_TYPES``. No other files need to change — the GUI dropdown,
Connect / Open dispatch, and settings persistence all adapt automatically.

Only implemented source types should appear here. Add entries as each
source type is built; do not add placeholder entries for future types.

``dialog_type`` controls what "Connect / Open" opens:
- ``"file_browser"`` — OS native file / folder picker (CSV, FGDB, Shapefile)
- ``"connection_form"`` — custom field dialog (Database, ArcGIS REST, WMS)

For ``"file_browser"`` types, ``file_types`` is a list of
``(label, pattern)`` tuples passed directly to ``tkinter.filedialog``.
For ``"connection_form"`` types, ``file_types`` is empty — the form
fields are declared on the connection-level config (e.g.
``DatabaseDriverConfig.fields``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class DataSourceTypeConfig:
    """Describes one supported data source type.

    Attributes:
        type_key: Unique identifier matching ``DataSourceConfig.source_type``
            and used in ``app_settings.json`` persistence.
        display_name: Label shown in the data source type dropdown.
        dialog_type: Controls what "Connect / Open" triggers.
            ``"file_browser"`` opens an OS file picker; ``"connection_form"``
            opens a custom Tkinter form dialog.
        file_types: File filter tuples for ``tkinter.filedialog`` — only
            used when ``dialog_type="file_browser"``. Each tuple is
            ``(label, glob_pattern)``, e.g. ``("CSV files", "*.csv")``.
        notes: Optional human-readable note shown in the GUI or help text.
    """

    type_key: str
    display_name: str
    dialog_type: str
    file_types: List[Tuple[str, str]] = field(default_factory=list)
    notes: str = ""


DATA_SOURCE_TYPES: List[DataSourceTypeConfig] = [
    DataSourceTypeConfig(
        type_key="csv",
        display_name="CSV File",
        dialog_type="file_browser",
        file_types=[("CSV files", "*.csv"), ("All files", "*.*")],
    ),
    DataSourceTypeConfig(
        type_key="database",
        display_name="Database (SQL)",
        dialog_type="connection_form",
        notes="PostgreSQL, Oracle, SQL Server, and others via SQLAlchemy.",
    ),
    # Future entries — add here as each source type is implemented:
    # DataSourceTypeConfig(
    #     type_key="arcgis_rest",
    #     display_name="ArcGIS REST Service",
    #     dialog_type="connection_form",
    # ),
    # DataSourceTypeConfig(
    #     type_key="wms",
    #     display_name="WMS REST Service",
    #     dialog_type="connection_form",
    # ),
    # DataSourceTypeConfig(
    #     type_key="fgdb",
    #     display_name="Esri File Geodatabase",
    #     dialog_type="file_browser",
    #     file_types=[("File Geodatabase", "*.gdb"), ("All files", "*.*")],
    # ),
    # DataSourceTypeConfig(
    #     type_key="shapefile",
    #     display_name="Shapefile",
    #     dialog_type="file_browser",
    #     file_types=[("Shapefiles", "*.shp"), ("All files", "*.*")],
    # ),
]

# Lookup by type_key for O(1) access.
TYPE_BY_KEY: dict = {t.type_key: t for t in DATA_SOURCE_TYPES}


def get_source_type(type_key: str) -> DataSourceTypeConfig:
    """Return the ``DataSourceTypeConfig`` for ``type_key``.

    Args:
        type_key: Key matching a ``DataSourceTypeConfig.type_key`` in
            ``DATA_SOURCE_TYPES``.

    Returns:
        The matching ``DataSourceTypeConfig``.

    Raises:
        KeyError: If ``type_key`` is not registered.
    """
    if type_key not in TYPE_BY_KEY:
        raise KeyError(
            f"Unknown data source type key: '{type_key}'. "
            f"Available keys: {list(TYPE_BY_KEY)}"
        )
    return TYPE_BY_KEY[type_key]


def get_display_names() -> List[str]:
    """Return display names for all registered source types, in order.

    Used to populate the data source type dropdown in the GUI.

    Returns:
        List of ``display_name`` strings in ``DATA_SOURCE_TYPES`` order.
    """
    return [t.display_name for t in DATA_SOURCE_TYPES]


def get_type_by_display_name(display_name: str) -> Optional[DataSourceTypeConfig]:
    """Return the config whose ``display_name`` matches, or ``None``.

    Used to resolve the user's dropdown selection back to a config.

    Args:
        display_name: The display name string as shown in the dropdown.

    Returns:
        Matching ``DataSourceTypeConfig``, or ``None`` if not found.
    """
    for t in DATA_SOURCE_TYPES:
        if t.display_name == display_name:
            return t
    return None
