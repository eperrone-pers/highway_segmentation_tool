"""Route identifier utilities.

This module centralizes route-id normalization rules so that route filtering,
optimization, export, and visualization all treat route identifiers the same.

A normalized route id is either:
- `None` (meaning "no route" / missing / invalid), or
- a stripped string value.

Important: This module intentionally avoids importing pandas/numpy/tkinter.
"""

from __future__ import annotations

import math
from typing import Any, Optional


# UI sentinel used in the route-column dropdown to indicate single-route mode.
# Centralized here so it is consistent across UI, controller, and visualization.
ROUTE_COLUMN_NONE_SENTINEL = "None - treat as single route"

# Internal/sentinel route IDs that should never be treated as real routes.
# Stored in lower-case for easy comparisons against normalized lower-case values.
INTERNAL_ROUTE_IDS_TO_SKIP_LOWER = {"_combined_data_"}


def normalize_route_id(value: Any) -> Optional[str]:
    """Normalize a route identifier to a stable string form.

    Rules:
    - `None` -> None
    - NaN-like values (float/numpy nan, pandas missing) -> None
    - Empty/whitespace-only strings -> None
    - Otherwise -> `str(value).strip()`

    Important: literal strings like "nan", "null", or "none" are treated as
    real route IDs if they appear in the input data.

    Args:
        value: Any route identifier (string, number, etc.).

    Returns:
        Normalized route id string, or None if the value is missing/invalid.
    """
    if value is None:
        return None

    # Treat numeric NaN / missing sentinel values as missing.
    # This preserves literal text values like "nan" (string) as data.
    try:
        if isinstance(value, (float, int)) and math.isnan(value):
            return None
    except Exception:
        pass

    # Catch numpy.nan and other NaN-like values (NaN != NaN).
    try:
        if value != value:  # noqa: PLR0124
            return None
    except Exception:
        # Some missing sentinels (e.g. pandas.NA) raise on truthiness/comparison.
        # Treat them as missing.
        return None

    route_str = str(value).strip()
    if not route_str:
        return None

    # pandas string dtype can surface missing values as the literal "<NA>"
    if route_str == "<NA>":
        return None

    return route_str


def filter_data_by_route(data, route_column: str, route_value: Any):
    """Filter a DataFrame to rows matching a specific route identifier.

    Route values are normalized before comparison to handle mixed types
    (e.g., integer 268296608 in data vs string "268296608" from the UI).

    Args:
        data: DataFrame with highway data.
        route_column: Name of the route column.
        route_value: Route identifier to filter by.

    Returns:
        Copy of rows where the route column matches route_value.
        Returns a full-DataFrame copy if route_column is absent, or an empty
        frame if route_value normalizes to None.
    """
    if route_column not in data.columns:
        return data.copy()

    route_str = normalize_route_id(route_value)
    if route_str is None:
        return data.iloc[0:0].copy()

    route_series = data[route_column].astype("string").str.strip()
    return data.loc[route_series == route_str].copy()


def list_routes(df, route_column: str) -> list:
    """Return sorted list of normalized, non-internal route IDs from df[route_column].

    Rows whose identifiers normalize to None (missing/invalid) and internal
    sentinel IDs (INTERNAL_ROUTE_IDS_TO_SKIP_LOWER) are silently excluded.

    Args:
        df: DataFrame containing a route column.
        route_column: Name of the column holding route identifiers.

    Returns:
        Sorted list of unique normalized route ID strings.
    """
    normalized = df[route_column].apply(normalize_route_id)
    routes = []
    for route_str in normalized.dropna():
        s = str(route_str)
        if s.lower() not in INTERNAL_ROUTE_IDS_TO_SKIP_LOWER:
            routes.append(s)
    return sorted(set(routes))


def prepare_routes_for_optimization(
    original_data,
    route_column,
    selected_routes: list,
    x_column: str,
    y_column: str,
    gap_threshold: float = 10000,
    is_single_route_mode: bool = False,
    preprocessing_config=None,
    must_break_columns=None,
    secondary_break_columns=None,
    log_callback=None,
) -> tuple:
    """Filter and gap-analyse each selected route, returning ready-to-optimize objects.

    Separating this step from optimization allows early detection of per-route
    data problems before any expensive GA work starts.

    Routes with fewer than 3 data points are skipped with a warning. Per-route
    failures are caught and logged so remaining routes still run.

    Args:
        original_data: Loaded RouteAnalysis object whose route_data contains all routes.
        route_column: Column name used to split routes, or None in single-route mode.
        selected_routes: Ordered list of route ID strings to process.
        x_column: Column name for the x-axis (milepoint / distance).
        y_column: Column name for the y-axis (condition value).
        gap_threshold: Maximum gap in x_column units that triggers a forced breakpoint.
        is_single_route_mode: When True, uses the entire route_data DataFrame as-is.
        preprocessing_config: PreprocessingRunConfig with preprocessing methods/params.
        must_break_columns: Columns that force mandatory attribute breaks.
        secondary_break_columns: Columns that force secondary attribute breaks.
        log_callback: Callable(str) for progress messages; silently ignored if None.

    Returns:
        Tuple of (prepared_routes, preprocessed_data_by_route) where:
        - prepared_routes is a list of (route_id, RouteAnalysis, preprocessing_results)
          tuples in selected_routes order, containing only successfully prepared routes.
        - preprocessed_data_by_route is a dict mapping route_id -> DataFrame
          (preprocessed when preprocessing was applied, otherwise original data).
    """
    from data_loader import analyze_route_gaps, process_route_with_preprocessing

    def log(msg: str) -> None:
        if log_callback:
            log_callback(msg)

    has_preprocessing = bool(
        preprocessing_config and (
            preprocessing_config.pre_gap_method
            or preprocessing_config.primary_method
            or preprocessing_config.secondary_method
        )
    )

    prepared_routes = []
    preprocessed_data_by_route: dict = {}
    log("Preparing route analyses...")

    for route_idx, route_id in enumerate(selected_routes, 1):
        try:
            log(f"Analyzing Route {route_id} ({route_idx}/{len(selected_routes)})...")

            if is_single_route_mode:
                route_data_df = original_data.route_data.copy()
            else:
                route_data_df = filter_data_by_route(original_data.route_data, route_column, route_id)

            if len(route_data_df) < 3:
                log(f"Warning: Route {route_id} has insufficient data ({len(route_data_df)} points), skipping...")
                continue

            # Sort within this route only — mixing rows across routes corrupts gap detection.
            route_data_df = route_data_df.sort_values(x_column).reset_index(drop=True)

            preprocessing_results = None
            if has_preprocessing:
                route_analysis, preprocessing_results = process_route_with_preprocessing(
                    route_data_df,
                    x_column,
                    y_column,
                    route_id=route_id,
                    gap_threshold=gap_threshold,
                    preprocessing_config=preprocessing_config,
                    first_attribute_columns=must_break_columns,
                    second_attribute_columns=secondary_break_columns,
                    log_callback=log_callback,
                )
            else:
                route_analysis = analyze_route_gaps(
                    route_data_df,
                    x_column,
                    y_column,
                    route_id=route_id,
                    gap_threshold=gap_threshold,
                    must_break_columns=must_break_columns,
                    secondary_break_columns=secondary_break_columns,
                )

            log(
                f"Route {route_id}: {len(route_analysis.route_data)} points, "
                f"{len(route_analysis.gap_segments)} gaps, "
                f"{len(route_analysis.mandatory_breakpoints)} mandatory breakpoints"
            )

            preprocessed_data_by_route[route_id] = route_analysis.route_data.copy()
            prepared_routes.append((route_id, route_analysis, preprocessing_results))

        except Exception as e:
            log(f"Error analyzing route {route_id}: {str(e)}")
            continue

    if prepared_routes:
        log(f"Route analysis completed: {len(prepared_routes)}/{len(selected_routes)} routes ready for optimization")
    else:
        log("ERROR: No routes could be analyzed successfully")

    return prepared_routes, preprocessed_data_by_route


def normalize_route_column_selection(value: Any) -> Optional[str]:
    """Normalize a route column selection from the UI.

    The UI uses a sentinel label (ROUTE_COLUMN_NONE_SENTINEL) to represent
    "no route column" (single-route mode). This helper converts UI values to a
    stable internal representation.

    Rules:
    - None -> None
    - Empty/whitespace-only -> None
    - Exact match of ROUTE_COLUMN_NONE_SENTINEL -> None
    - Otherwise -> stripped string
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None
    if text == ROUTE_COLUMN_NONE_SENTINEL:
        return None
    return text
