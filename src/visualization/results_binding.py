"""Results binding helpers for enhanced visualization.

These functions keep results-schema extraction and light data wrangling
(routes, grouping, file info parsing, x/y column mapping) separate from the
tkinter/matplotlib UI code.

All helpers are designed to be pure and easy to unit test.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from route_utils import normalize_route_id


@dataclass(frozen=True)
class XYColumnResolution:
    x_col: Optional[str]
    y_col: Optional[str]
    error_message: Optional[str] = None


def resolve_xy_columns(json_results: Dict[str, Any]) -> XYColumnResolution:
    """Resolve x/y column names from the results JSON.

    Resolution order (behavior matches historical UI intent):
    1) input_parameters.route_processing.{x_column,y_column}
    2) analysis_metadata.input_file_info.column_info.{x_column,y_column}

    In strict mode, if either is missing we return an error message.
    """

    json_results = json_results or {}

    route_processing = (
        json_results.get("input_parameters", {})
        .get("route_processing", {})
        or {}
    )

    x_col = route_processing.get("x_column")
    y_col = route_processing.get("y_column")

    if not x_col or not y_col:
        column_info = (
            json_results.get("analysis_metadata", {})
            .get("input_file_info", {})
            .get("column_info", {})
            or {}
        )

        if not x_col:
            x_col = column_info.get("x_column")
        if not y_col:
            y_col = column_info.get("y_column")

    if not x_col or not y_col:
        return XYColumnResolution(
            x_col=x_col or None,
            y_col=y_col or None,
            error_message=(
                f"Missing column information in results JSON: x_column={x_col}, y_column={y_col}. "
                "This indicates a corrupted or outdated results file."
            ),
        )

    return XYColumnResolution(x_col=str(x_col), y_col=str(y_col))


def routes_from_json_results(json_results: Optional[Dict[str, Any]]) -> List[str]:
    """Extract normalized route ids from results JSON (schema-driven)."""

    routes: List[str] = []
    if not json_results:
        return routes

    route_results = json_results.get("route_results", [])
    if isinstance(route_results, list):
        for route_result in route_results:
            try:
                route_id = (route_result or {}).get("route_info", {}).get("route_id", "Unknown")
            except Exception:
                route_id = "Unknown"
            route_str = normalize_route_id(route_id) or "Unknown"
            routes.append(route_str)

    return routes


def routes_from_original_data(original_data: Optional[pd.DataFrame], route_column: Optional[str]) -> List[str]:
    """Extract normalized route ids from original data (best-effort fallback)."""

    if original_data is None or original_data.empty:
        return []
    if not route_column or route_column not in original_data.columns:
        return []

    unique_routes = list(original_data[route_column].unique())
    normalized = [normalize_route_id(route) for route in unique_routes]
    return [r for r in normalized if r is not None]


def resolve_routes(
    json_results: Optional[Dict[str, Any]],
    original_data: Optional[pd.DataFrame],
    route_column: Optional[str],
) -> List[str]:
    """Resolve route list for the visualization.

    Priority:
    1) Use routes embedded in results JSON.
    2) If missing, fall back to routes in original data using route_column.
    3) If still missing, return ['Unknown Route'].
    """

    routes = routes_from_json_results(json_results)
    if not routes:
        routes = routes_from_original_data(original_data, route_column)

    if not routes:
        return ["Unknown Route"]

    # De-dup while preserving order
    seen = set()
    ordered: List[str] = []
    for r in routes:
        if r not in seen:
            seen.add(r)
            ordered.append(r)
    return ordered


def original_data_path_from_results(json_results: Optional[Dict[str, Any]]) -> Optional[str]:
    """Return the original data file path from the results JSON schema, if present."""

    if not json_results:
        return None
    info = json_results.get("analysis_metadata", {}).get("input_file_info", {})
    if not isinstance(info, dict):
        return None
    path = info.get("data_file_path")
    return str(path) if path else None


def find_existing_original_data_file(path: Optional[str]) -> Optional[str]:
    """Return the path if it exists on disk; otherwise None."""

    if not path:
        return None
    p = Path(path)
    return str(p) if p.exists() else None


def group_original_data_by_route(
    original_data: pd.DataFrame,
    routes: Iterable[str],
    route_column: Optional[str],
) -> Dict[str, pd.DataFrame]:
    """Group original data into a dict of route_id -> DataFrame.

    If route_column is missing/unavailable, all data is assigned to the first route.
    """

    grouped: Dict[str, pd.DataFrame] = {}

    routes_list = [normalize_route_id(r) for r in routes]
    routes_list = [r for r in routes_list if r is not None]

    if route_column and route_column in original_data.columns:
        route_series = original_data[route_column].astype("string").str.strip()
        for route_id in routes_list:
            route_data = original_data.loc[route_series == route_id].copy()
            if not route_data.empty:
                grouped[route_id] = route_data
        return grouped

    # Single-route fallback
    if routes_list:
        grouped[routes_list[0]] = original_data.copy()
    else:
        grouped["Unknown Route"] = original_data.copy()
    return grouped
