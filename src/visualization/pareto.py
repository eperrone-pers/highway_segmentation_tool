"""Pareto-front helpers.

These helpers extract objective series from saved results and apply any
configuration-driven transforms (e.g., negate) for display.

Matplotlib rendering remains in `visualization_ui.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from config import get_optimization_method


@dataclass(frozen=True)
class ParetoSeries:
    x_values: List[float]
    y_values: List[float]
    point_ids: List[int]
    x_label: str
    y_label: str
    warning: Optional[str] = None


_DEFAULT_X_LABEL = "X-Axis Label (Configure in config.py objective_plot_configs)"
_DEFAULT_Y_LABEL = "Y-Axis Label (Configure in config.py objective_plot_configs)"


def prepare_pareto_series(
    json_results: Optional[Dict[str, Any]],
    pareto_points: Sequence[Dict[str, Any]],
) -> ParetoSeries:
    """Prepare 2D Pareto series for plotting.

    - Extracts objective_values[0:2] for each pareto point.
    - Applies configuration-driven axis transforms (currently: transform == 'negate').
    - Returns axis labels from configuration when available.

    Returns empty series if the input points do not contain usable 2D objectives.
    """

    x_vals: List[float] = []
    y_vals: List[float] = []
    point_ids: List[int] = []

    for point in pareto_points:
        objectives = point.get("objective_values", [])
        if isinstance(objectives, (list, tuple)) and len(objectives) >= 2:
            try:
                x_vals.append(float(objectives[0]))
                y_vals.append(float(objectives[1]))
                point_ids.append(int(point.get("point_id", 0) or 0))
            except Exception:
                # Skip points with non-numeric objectives
                continue

    x_label = _DEFAULT_X_LABEL
    y_label = _DEFAULT_Y_LABEL

    warning: Optional[str] = None

    if not x_vals or not y_vals:
        return ParetoSeries(x_vals, y_vals, point_ids, x_label, y_label, warning=None)

    analysis_method = (json_results or {}).get("analysis_metadata", {}).get("analysis_method", "multi")

    try:
        method_config = get_optimization_method(analysis_method)
        plot_configs = getattr(method_config, "objective_plot_configs", None)

        if plot_configs and len(plot_configs) >= 2:
            x_config = plot_configs[0]
            y_config = plot_configs[1]

            if getattr(x_config, "transform", None) == "negate":
                x_vals = [-x for x in x_vals]

            if getattr(y_config, "transform", None) == "negate":
                y_vals = [-y for y in y_vals]

            if getattr(x_config, "name", None):
                x_label = x_config.name
            if getattr(y_config, "name", None):
                y_label = y_config.name

    except Exception as exc:
        warning = f"Could not apply axis transforms from config: {exc}"

    return ParetoSeries(x_vals, y_vals, point_ids, x_label, y_label, warning=warning)


def choose_selected_pareto_point(
    pareto_points: Sequence[Dict[str, Any]],
    selected_point_id: Optional[Any],
) -> Optional[Dict[str, Any]]:
    """Return the selected pareto point dict, falling back to the first.

    Behavior matches the existing UI logic:
    - If `selected_point_id` is provided and matches a point's `point_id`, return it.
    - Otherwise, return the first point.
    - If `pareto_points` is empty, return None.
    """

    if not pareto_points:
        return None

    if selected_point_id is not None:
        for point in pareto_points:
            if point.get("point_id") == selected_point_id:
                return point

    return pareto_points[0]
