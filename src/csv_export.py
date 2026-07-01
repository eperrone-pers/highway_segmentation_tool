"""Segment-level CSV export for highway segmentation results.

Reads the JSON output produced by the analysis pipeline and writes a flat CSV
where each row is one segment from the best (first pareto) solution per route.

Base columns: route_id[, route][, direction][, lane], segment_index, start, end,
              length, point_count, <y_col>_avg, <y_col>_min, <y_col>_max,
              <y_col>_std, is_mandatory

When a composite route key was used (direction_column and/or lane_column active),
the individual ``route``, ``direction``, and ``lane`` fields present in
``route_info`` are inserted as separate columns immediately after ``route_id``.
Only columns that were active (present in ``route_info``) are emitted.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import pandas as pd

_logger = logging.getLogger(__name__)

# Ordered list of optional component column names as they should appear in CSV.
_COMPONENT_FIELDS = ("route", "direction", "lane")


def segments_to_dataframe(json_data: Dict[str, Any]) -> pd.DataFrame:
    """Build a flat segments DataFrame from parsed JSON results.

    Uses the first pareto point (best / representative solution) for each
    route. For single-objective and constrained methods this is the only
    point; for NSGA-II it is the first Pareto-front solution.

    When the results contain composite route keys (direction_column or
    lane_column was active), the individual ``route``, ``direction``, and
    ``lane`` fields are added as columns immediately after ``route_id``.

    Args:
        json_data: Parsed JSON results dict as produced by the analysis
            pipeline.

    Returns:
        DataFrame with one row per segment. Empty if no segment_details are
        found in any route.
    """
    y_col = (
        json_data.get("input_parameters", {})
        .get("configuration", {})
        .get("y_column", "y_value")
    )
    y_col_safe = str(y_col).replace(" ", "_")

    rows: List[Dict[str, Any]] = []

    for route_result in json_data.get("route_results", []):
        route_info = route_result.get("route_info", {})
        route_id = route_info.get("route_id", "unknown")

        # Collect whichever optional component fields are present in route_info.
        component_values: Dict[str, str] = {
            field: route_info[field]
            for field in _COMPONENT_FIELDS
            if field in route_info
        }

        pareto_points = (
            route_result.get("processing_results", {}).get("pareto_points", [])
        )
        if not pareto_points:
            _logger.warning("Route %r: no pareto_points found — skipping", route_id)
            continue

        segment_details = (
            pareto_points[0].get("segmentation", {}).get("segment_details", [])
        )
        if not segment_details:
            _logger.warning(
                "Route %r: no segment_details in first pareto point — skipping",
                route_id,
            )
            continue

        for seg in segment_details:
            row: Dict[str, Any] = {"route_id": route_id}
            row.update(component_values)
            row.update(
                {
                    "segment_index": seg.get("segment_index"),
                    "start": seg.get("start"),
                    "end": seg.get("end"),
                    "length": seg.get("length"),
                    "point_count": seg.get("data_point_count"),
                    f"{y_col_safe}_avg": seg.get("y_value_avg"),
                    f"{y_col_safe}_min": seg.get("y_value_min"),
                    f"{y_col_safe}_max": seg.get("y_value_max"),
                    f"{y_col_safe}_std": seg.get("y_value_std"),
                    "is_mandatory": seg.get("is_mandatory"),
                }
            )
            rows.append(row)

    return pd.DataFrame(rows)


def export_json_to_csv(
    json_path: Union[str, Path],
    csv_path: Union[str, Path],
) -> Tuple[bool, str]:
    """Export segment results from a JSON results file to a flat CSV file.

    Args:
        json_path: Path to the analysis JSON results file.
        csv_path: Destination path for the output CSV file.

    Returns:
        Tuple of (success, error_message). On success, error_message is "".
    """
    try:
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"Could not read JSON: {exc}"

    try:
        df = segments_to_dataframe(data)
    except Exception as exc:
        return False, f"Could not build segments DataFrame: {exc}"

    if df.empty:
        return False, "No segment_details found in results — CSV not written."

    try:
        df.to_csv(csv_path, index=False)
    except Exception as exc:
        return False, f"Could not write CSV: {exc}"

    return True, ""
