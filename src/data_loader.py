import pandas as pd
from dataclasses import dataclass
import logging
from typing import List, Set, Dict, Tuple, Optional

from route_utils import normalize_route_id

logger = logging.getLogger(__name__)


@dataclass
class RouteAnalysis:
    """
    Comprehensive analysis of route/sequence data.
    
    This dataclass contains all necessary data structures for gap-aware optimization:
    
    route_data: Full route definition with all data points
    gap_segments: Detected gap segments representing regions with no data collection
    mandatory_breakpoints: Required breakpoints (gaps + route boundaries)
    valid_x_values: Original X values excluding those inside merged gap regions
    data_range: Min/max bounds for X and Y values (essential for visualization)
    route_stats: Summary statistics for debugging and validation
    """
    route_id: str
    route_data: pd.DataFrame  # Full route data with all points
    gap_segments: List[Tuple[float, float]]  # Gap segments [(start_x, end_x), ...]
    mandatory_breakpoints: Set[float]  # Required breakpoints (gaps + boundaries)
    valid_x_values: List[float]  # All X values excluding gap regions
    data_range: Dict[str, float]  # {'x_min': float, 'x_max': float, 'y_min': float, 'y_max': float}
    route_stats: Dict  # Summary stats: total_points, gap_count, valid_range, etc.


def analyze_route_gaps(
    df: pd.DataFrame,
    x_column: str,
    y_column: str,
    route_id: str = "default",
    gap_threshold: float = None,
) -> RouteAnalysis:
    """
    Analyze route data to detect gaps and create comprehensive RouteAnalysis.
    
    This function:
    1. Detects data gaps using consecutive position differences
    2. Merges adjacent gaps with warnings
    3. Validates route endpoints (gaps at start/end are fatal errors)
    4. Creates all data structures needed for gap-aware optimization
    
    Args:
        df: DataFrame with position and data columns
        x_column: Name of the X-axis column (typically position/distance)
        y_column: Name of the Y-axis column (typically the measured values)
        route_id: Identifier for the route
        
    Returns:
        RouteAnalysis: Complete route analysis with gap detection
        
    Raises:
        ValueError: If gaps exist at route start or end (fatal error)
    """
    # Only show detailed analysis for actual routes (not internal combined analysis)
    show_output = not route_id.startswith("_") and route_id != "default"
    
    if show_output:
        logger.info("=== Analyzing Route: %s ===", route_id)
        logger.info("Total data points (raw): %s", len(df))
    
    # Sort by X column to ensure proper gap detection
    df_sorted = df.sort_values(x_column).copy()
    x_values = df_sorted[x_column].tolist()
    
    if show_output:
        logger.info("Route range: %.3f to %.3f units", x_values[0], x_values[-1])
    
    if gap_threshold is None:
        raise ValueError("gap_threshold must be provided (got None)")
    if gap_threshold <= 0:
        raise ValueError(f"gap_threshold must be > 0 (got {gap_threshold})")

    # Detect gaps using consecutive X-value differences
    gaps = []
    
    for current_x, next_x in zip(x_values, x_values[1:]):
        gap_size = next_x - current_x
        
        if gap_size > gap_threshold:
            gaps.append((current_x, next_x))
            if show_output:
                logger.info(
                    "Detected gap: %.3f to %.3f units (size: %.3f)",
                    current_x,
                    next_x,
                    gap_size,
                )
    
    if show_output:
        logger.info("Total gaps detected: %s", len(gaps))
    
    # Merge only truly consecutive gaps (touching/overlapping boundaries).
    # This groups runs of consecutive long-spacing into a single long gap,
    # but does NOT merge gaps separated by a valid non-gap spacing.
    processed_gaps = _merge_adjacent_gaps(gaps)
    _validate_route_endpoints(processed_gaps, x_values[0], x_values[-1])
    
    # Create mandatory breakpoints (gap boundaries + route boundaries)
    mandatory_breakpoints = set()
    mandatory_breakpoints.add(x_values[0])  # Route start
    mandatory_breakpoints.add(x_values[-1])  # Route end
    
    for start_mile, end_mile in processed_gaps:
        mandatory_breakpoints.add(start_mile)  # Gap start
        mandatory_breakpoints.add(end_mile)    # Gap end
    
    # After gap merging, some original points may fall inside merged gap regions.
    # Those interior points are ignored/removed from the dataset used downstream.
    in_merged_gap_mask = df_sorted[x_column].apply(
        lambda x_val: any(gap_start < x_val < gap_end for gap_start, gap_end in processed_gaps)
    )

    df_valid = df_sorted.loc[~in_merged_gap_mask].copy()
    valid_x_values = df_valid[x_column].tolist()
    points_excluded = int(in_merged_gap_mask.sum())

    if show_output and points_excluded:
        logger.info("Excluded %s interior points inside merged gaps", points_excluded)
    if show_output:
        logger.info("Valid X values (excluding merged gap interiors): %s", len(valid_x_values))
        logger.info("Mandatory breakpoints: %s", len(mandatory_breakpoints))
    
    # Calculate data range bounds for visualization and schema compliance
    y_values = df_valid[y_column].tolist()
    data_range = {
        'x_min': float(x_values[0]),   # Route start (mandatory breakpoint) 
        'x_max': float(x_values[-1]),  # Route end (mandatory breakpoint)
        'y_min': float(min(y_values)), # Minimum Y value across route
        'y_max': float(max(y_values))  # Maximum Y value across route
    }
    
    # Create route statistics
    route_stats = {
        'raw_points': len(df),
        'total_points': len(df_valid),
        'gap_count': len(processed_gaps),  
        'valid_points': len(valid_x_values),
        'route_start': x_values[0],
        'route_end': x_values[-1],
        'total_length': x_values[-1] - x_values[0],
        'gap_total_length': sum(end - start for start, end in processed_gaps),
        'valid_length': x_values[-1] - x_values[0] - sum(end - start for start, end in processed_gaps)
    }
    
    if show_output:
        logger.info("Route statistics:")
        logger.info("  Total length: %.3f units", route_stats["total_length"])
        logger.info("  Gap total length: %.3f units", route_stats["gap_total_length"])
        logger.info("  Valid length: %.3f units", route_stats["valid_length"])
        logger.info(
            "  Data range: X[%.3f to %.3f], Y[%.1f to %.1f]",
            data_range["x_min"],
            data_range["x_max"],
            data_range["y_min"],
            data_range["y_max"],
        )
        logger.info("  Points excluded by merged gaps: %s", points_excluded)
    
    return RouteAnalysis(
        route_id=route_id,
        route_data=df_valid,
        gap_segments=processed_gaps,
        mandatory_breakpoints=mandatory_breakpoints,
        valid_x_values=valid_x_values,
        data_range=data_range,
        route_stats=route_stats
    )


def _merge_adjacent_gaps(gaps: List[Tuple[float, float]], merge_epsilon: float = 1e-9) -> List[Tuple[float, float]]:
    """
    Merge consecutive gaps (touching/overlapping).
    
    This merges only gaps that share a boundary (or overlap due to floating point noise).
    It does NOT merge gaps that are separated by any positive-length non-gap spacing.
    
    Args:
        gaps: List of gap tuples [(start, end), ...]
        merge_epsilon: Small tolerance for floating point comparisons
        
    Returns:
        List of merged gap tuples
    """
    if not gaps:
        return []
        
    # Sort gaps by start position
    sorted_gaps = sorted(gaps)
    merged = []
    current_start, current_end = sorted_gaps[0]
    
    for start, end in sorted_gaps[1:]:
        # Merge only if touching/overlapping (consecutive gaps)
        if start <= current_end + merge_epsilon:
            current_end = max(current_end, end)
        else:
            merged.append((current_start, current_end))
            current_start, current_end = start, end
    
    merged.append((current_start, current_end))
    
    if len(merged) < len(sorted_gaps):
        logger.debug(
            "Gap merging: %s raw gaps -> %s merged gaps",
            len(sorted_gaps),
            len(merged),
        )
    
    return merged


def _validate_route_endpoints(gaps: List[Tuple[float, float]], route_start: float, route_end: float):
    """
    Validate that no gaps exist at route start or end.
    
    Gaps at route boundaries are fatal errors that prevent proper optimization.
    
    Args:
        gaps: List of gap tuples
        route_start: First milepoint in route
        route_end: Last milepoint in route
        
    Raises:
        ValueError: If gaps exist at route boundaries
    """
    tolerance = 1e-6  # Small tolerance for floating point comparison
    
    for gap_start, gap_end in gaps:
        if abs(gap_start - route_start) < tolerance:
            raise ValueError(f"FATAL: Gap at route start ({route_start:.3f}). Cannot optimize.")
        if abs(gap_end - route_end) < tolerance:
            raise ValueError(f"FATAL: Gap at route end ({route_end:.3f}). Cannot optimize.")


def prepare_route_processing(data, route_column=None, selected_routes=None, data_filename=None):
    """
    Prepare route processing information for optimization.
    
    Args:
        data: DataFrame with highway data
        route_column: Name of the route column (if any)
        selected_routes: List of route identifiers to process
        data_filename: Filename when using filename-as-route mode
    
    Returns:
        dict: Route processing information
    """
    if route_column and route_column in data.columns and selected_routes:
        # Multi-route column-based processing 
        return {
            'processing_mode': 'multi_route_column',
            'routes_to_process': selected_routes,
            'route_column': route_column,
            'data': data
        }
    elif data_filename:
        # Single route using filename
        return {
            'processing_mode': 'single_route_filename', 
            'routes_to_process': [data_filename],
            'route_column': None,
            'data': data
        }
    else:
        # Default single route processing
        return {
            'processing_mode': 'single_route',
            'routes_to_process': ['default'],
            'route_column': None,
            'data': data
        }

def filter_data_by_route(data, route_column, route_value):
    """
    Filter data by a specific route value.
    
    Args:
        data: DataFrame with highway data
        route_column: Name of the route column
        route_value: Route identifier to filter by
    
    Returns: 
        DataFrame: Filtered data for the specific route
    """
    if route_column not in data.columns:
        return data.copy()

    # Treat route identifiers as categorical strings regardless of CSV inference.
    # This avoids mismatches like int 268296608 (data) vs "268296608" (UI selection).
    route_str = normalize_route_id(route_value)
    if route_str is None:
        return data.iloc[0:0].copy()

    route_series = data[route_column].astype("string").str.strip()
    return data.loc[route_series == route_str].copy()


def load_highway_data(file_path: str) -> Optional[pd.DataFrame]:
    """Load highway data from a CSV file.

    This is a small compatibility wrapper used by integration demos/tests.
    Production code typically loads data through the GUI/file manager.
    """
    try:
        return pd.read_csv(file_path)
    except Exception as exc:
        logger.exception("Error loading data from %r", file_path)
        return None

